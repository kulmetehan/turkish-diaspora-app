// src/components/MapView.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import mapboxgl, { Map as MapboxMap } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";
import { createRoot, type Root } from "react-dom/client";

import PreviewTooltip from "@/components/PreviewTooltip";
import MarkerLayer from "./MarkerLayer";
import { cn } from "@/lib/ui/cn";

// Zorg dat je VITE_MAPBOX_TOKEN in .env staat
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

type Props = {
  locations: LocationMarker[];
  highlightedId: string | null;
  detailId: string | null;
  onHighlight?: (id: string | null) => void;
  onOpenDetail?: (id: string) => void;
  onMapClick?: () => void;
  onViewportChange?: (bbox: string | null) => void;
  interactionDisabled?: boolean;
};

/**
 * MapView: toont de Mapbox-kaart en de MarkerLayer.
 * - Houdt één map-instantie in leven
 * - Laat de gebruiker zelf de viewport beheren (geen auto-centering)
 */
export default function MapView({ locations, highlightedId, detailId, onHighlight, onOpenDetail, onMapClick, onViewportChange, interactionDisabled = false }: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const tooltipRef = useRef<{ popup: mapboxgl.Popup | null; root: Root | null; container: HTMLElement | null } | null>(null);
  const lastBboxRef = useRef<string | null>(null);

  // Init Map slechts één keer
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapRef.current) return; // guard against StrictMode double-invoke

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: import.meta.env.VITE_MAPBOX_STYLE || "mapbox://styles/mapbox/streets-v12",
      center: [4.4777, 51.9244], // Rotterdam default
      zoom: 11,
      attributionControl: false,
    });

    mapRef.current = map;

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");

    // Background click logic
    map.on("click", (e) => {
      if (!onMapClick) return;
      try {
        const feats = map.queryRenderedFeatures(e.point) as any[];
        const interactiveHit = Array.isArray(feats) && feats.some((f) => f?.layer?.id === "tda-unclustered-point" || f?.layer?.id === "tda-clusters" || f?.layer?.id === "tda-cluster-count");
        if (interactiveHit) return;
        const hiHit = Array.isArray(feats) && feats.some((f) => f?.layer?.id === "tda-highlight");
        if (hiHit) { onMapClick(); return; }
      } catch { }
      onMapClick();
    });

    map.on("load", () => {
      setMapReady(true);
    });

    return () => {
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch { }
        mapRef.current = null;
      }
    };
  }, []);

  // Notify parent about viewport changes (bbox) when map stops moving
  useEffect(() => {
    if (!mapReady) return;
    if (!onViewportChange) return;
    const map = mapRef.current;
    if (!map) return;

    const notify = () => {
      try {
        const bounds = map.getBounds?.();
        if (!bounds) {
          if (lastBboxRef.current !== null) {
            lastBboxRef.current = null;
            onViewportChange(null);
          }
          return;
        }

        const zoom = map.getZoom?.();
        const sw = bounds.getSouthWest?.();
        const ne = bounds.getNorthEast?.();
        if (!sw || !ne || typeof sw.lng !== "number" || typeof sw.lat !== "number" || typeof ne.lng !== "number" || typeof ne.lat !== "number") {
          if (lastBboxRef.current !== null) {
            lastBboxRef.current = null;
            onViewportChange(null);
          }
          return;
        }

        const isZoomedOut = typeof zoom === "number" && (zoom <= 2 || (ne.lng - sw.lng) > 180 || (ne.lat - sw.lat) > 90);
        const nextBbox = isZoomedOut ? null : `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`;
        if (lastBboxRef.current !== nextBbox) {
          lastBboxRef.current = nextBbox;
          onViewportChange(nextBbox);
        }
      } catch {
        if (lastBboxRef.current !== null) {
          lastBboxRef.current = null;
          onViewportChange(null);
        }
      }
    };

    notify();
    map.on("moveend", notify);

    return () => {
      try {
        map.off("moveend", notify);
      } catch {
        /* ignore */
      }
    };
  }, [mapReady, onViewportChange]);

  useEffect(() => {
    if (!mapReady) return;
    const map = mapRef.current;
    if (!map) return;

    const cleanup = () => {
      const current = tooltipRef.current;
      if (current?.root) {
        try {
          current.root.unmount();
        } catch {
          /* ignore */
        }
      }
      if (current?.popup) {
        try {
          current.popup.remove();
        } catch {
          /* ignore */
        }
      }
      tooltipRef.current = null;
    };

    if (!highlightedId || detailId) {
      cleanup();
      return;
    }

    const loc = locations.find((l) => String(l.id) === String(highlightedId));
    if (!loc || typeof loc.lng !== "number" || typeof loc.lat !== "number") {
      cleanup();
      return;
    }

    cleanup();

    const container = document.createElement("div");
    const root = createRoot(container);
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: [0, 14],
      anchor: "bottom",
      className: "tda-preview-popup",
    })
      .setLngLat([loc.lng, loc.lat])
      .setMaxWidth("0")
      .setDOMContent(container)
      .addTo(map);

    const popupEl = popup.getElement();
    popupEl.classList.add("tda-preview-popup");

    const handleClose = () => {
      onHighlight?.(null);
    };
    const handleDetail = () => {
      onOpenDetail?.(loc.id);
    };

    root.render(
      <PreviewTooltip
        location={loc}
        onRequestClose={handleClose}
        onRequestDetail={handleDetail}
      />
    );

    const positionPreviewAnchor = () => {
      const current = tooltipRef.current;
      if (!current) return;
      const element = popup.getElement();
      const card = element.querySelector(".tda-card") as HTMLElement | null;
      const content = element.querySelector(".mapboxgl-popup-content") as HTMLElement | null;
      if (!card || !content) return;

      const rect = card.getBoundingClientRect();
      const { width, height } = rect;
      const canvas = map.getCanvas();
      const vw = canvas.clientWidth;
      const vh = canvas.clientHeight;
      const point = map.project([loc.lng!, loc.lat!]);

      let anchor: "bottom" | "top" = "bottom";
      const margin = 8;
      const offsetY = 14;
      if (point.y - offsetY - height < margin) {
        anchor = "top";
      }

      let shiftX = 0;
      const halfW = width / 2;
      if (point.x - halfW < margin) {
        shiftX = halfW - point.x + margin;
      } else if (point.x + halfW > vw - margin) {
        shiftX = -(point.x + halfW - vw + margin);
      }

      element.classList.toggle("anchor-bottom", anchor === "bottom");
      element.classList.toggle("anchor-top", anchor === "top");

      content.style.transform = `translateX(${Math.round(shiftX)}px)`;
    };

    requestAnimationFrame(positionPreviewAnchor);
    const debounced = () => requestAnimationFrame(positionPreviewAnchor);
    map.on("move", debounced);
    map.on("resize", debounced);

    tooltipRef.current = { popup, root, container };

    popup.on("close", handleClose);

    return () => {
      cleanup();
      map.off("move", debounced);
      map.off("resize", debounced);
    };
  }, [highlightedId, detailId, locations, mapReady, onHighlight, onOpenDetail]);

  // Sluit popup bij unmount of style reset
  useEffect(() => {
    return () => {
      const current = tooltipRef.current;
      if (current?.root) {
        try {
          current.root.unmount();
        } catch {
          /* ignore */
        }
      }
      if (current?.popup) {
        try {
          current.popup.remove();
        } catch {
          /* ignore */
        }
      }
      tooltipRef.current = null;
    };
  }, []);

  return (
    <div
      ref={mapContainerRef}
      className={cn(
        "relative h-full w-full overflow-hidden rounded-lg shadow-md",
        interactionDisabled && "pointer-events-none"
      )}
    >
      {mapReady && mapRef.current && (
        <MarkerLayer
          map={mapRef.current}
          locations={locations}
          selectedId={highlightedId}
          onSelect={(id) => onHighlight?.(id)}
        />
      )}
    </div>
  );
}

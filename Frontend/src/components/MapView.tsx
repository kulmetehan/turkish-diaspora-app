// src/components/MapView.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import mapboxgl, { Map as MapboxMap } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";
import MarkerLayer from "./MarkerLayer";

// Zorg dat je VITE_MAPBOX_TOKEN in .env staat
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

type Props = {
  locations: LocationMarker[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
  onMapClick?: () => void;
  onViewportChange?: (bbox: string | null) => void;
};

/**
 * MapView: toont de Mapbox-kaart en de MarkerLayer.
 * - Houdt één map-instantie in leven
 * - Laat de gebruiker zelf de viewport beheren (geen auto-centering)
 */
export default function MapView({ locations, selectedId, onSelect, onMapClick, onViewportChange }: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
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

  // Highlight/popup sync bij selectie (zonder camera-bewegingen)
  useEffect(() => {
    if (!mapReady || !locations?.length) return;
    const map = mapRef.current;
    if (!map) return;

    // If deselected → remove popup (if any) and bail
    if (!selectedId) {
      try { popupRef.current?.remove(); } catch { }
      popupRef.current = null;
      try { map.getCanvas().style.cursor = ""; } catch { }
      return;
    }

    const loc = locations.find((l) => String(l.id) === String(selectedId));
    if (!loc) return;

    // Toon een popup met kerngegevens
    try {
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
      const html = `
        <div class="text-sm">
          <div class="font-semibold mb-1">${String(loc.name ?? "Onbekend")}</div>
          <div class="text-muted-foreground">${String(loc.category ?? "—")}</div>
          
        </div>
      `;
      const popup = new mapboxgl.Popup({ closeOnClick: false, offset: 12 })
        .setLngLat([loc.lng, loc.lat])
        .setHTML(html)
        .addTo(map);
      // F4-S1: nooit de camera verplaatsen tijdens selectie; enkel popup/highlight.
      // Zie TDA-129 + F4-S1 voor viewport-fetch constraints.
      // When the user closes the popup, treat it like a background tap (deselect)
      try {
        popup.on("close", () => { try { onMapClick?.(); } catch { } });
      } catch { }
      popupRef.current = popup;
    } catch { }
  }, [selectedId, mapReady, locations]);

  // Sluit popup bij unmount of style reset
  useEffect(() => {
    return () => {
      try {
        popupRef.current?.remove();
      } catch { }
      popupRef.current = null;
    };
  }, []);

  return (
    <div
      ref={mapContainerRef}
      className="relative w-full h-full rounded-lg overflow-hidden shadow-md"
    >
      {mapReady && mapRef.current && (
        <MarkerLayer
          map={mapRef.current}
          locations={locations}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      )}
    </div>
  );
}

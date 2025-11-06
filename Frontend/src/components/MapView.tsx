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
  bottomSheetHeight?: number;
};

/**
 * MapView: toont de Mapbox-kaart en de MarkerLayer.
 * - Houdt één map-instantie in leven
 * - Centreert vloeiend op geselecteerde locatie
 */
export default function MapView({ locations, selectedId, onSelect, onMapClick, onViewportChange, bottomSheetHeight }: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const popupRef = useRef<mapboxgl.Popup | null>(null);
  const debounceTimeoutRef = useRef<number | null>(null);
  const isProgrammaticMoveRef = useRef(false);
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

    // Handle viewport changes (pan/zoom) with debouncing
    const handleMoveEnd = () => {
      // Ignore moveend events triggered by programmatic map movements
      if (isProgrammaticMoveRef.current) {
        return;
      }
      
      if (!onViewportChange) return;
      
      // Clear existing timeout
      if (debounceTimeoutRef.current !== null) {
        window.clearTimeout(debounceTimeoutRef.current);
      }
      
      // Debounce viewport change callback
      debounceTimeoutRef.current = window.setTimeout(() => {
        // Double-check flag after debounce (in case programmatic move started during debounce)
        if (isProgrammaticMoveRef.current) {
          return;
        }
        
        try {
          const bounds = map.getBounds();
          if (!bounds) {
            const newBbox = null;
            if (lastBboxRef.current !== newBbox) {
              lastBboxRef.current = newBbox;
              onViewportChange(newBbox);
            }
            return;
          }
          
          // Check if fully zoomed out (zoom level <= 2 or very large bounds)
          const zoom = map.getZoom();
          const sw = bounds.getSouthWest();
          const ne = bounds.getNorthEast();
          
          // Consider fully zoomed out if zoom <= 2 or bounds span > 180 degrees
          const isZoomedOut = zoom <= 2 || (ne.lng - sw.lng) > 180 || (ne.lat - sw.lat) > 90;
          
          const newBbox = isZoomedOut ? null : `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`;
          
          // Only trigger callback if bbox actually changed (string comparison)
          if (lastBboxRef.current !== newBbox) {
            lastBboxRef.current = newBbox;
            onViewportChange(newBbox);
          }
        } catch (e) {
          console.warn("Error getting map bounds:", e);
          const newBbox = null;
          if (lastBboxRef.current !== newBbox) {
            lastBboxRef.current = newBbox;
            onViewportChange(newBbox);
          }
        }
      }, 200); // 200ms debounce
    };

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
      // Trigger initial viewport change after map loads
      if (onViewportChange) {
        // Small delay to ensure map is fully initialized
        setTimeout(() => {
          handleMoveEnd();
        }, 100);
      }
    });

    map.on("moveend", handleMoveEnd);

    return () => {
      if (debounceTimeoutRef.current !== null) {
        window.clearTimeout(debounceTimeoutRef.current);
      }
      if (mapRef.current) {
        try { mapRef.current.remove(); } catch { }
        mapRef.current = null;
      }
    };
  }, [onViewportChange]);

  // Vloeiend centreren bij klik op lijst-item
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

    // Calculate offset to keep marker visible above bottom sheet
    let offsetY = 0;
    if (bottomSheetHeight && bottomSheetHeight > 0) {
      // Place target above center by ~half of the sheet height
      offsetY = -Math.round(bottomSheetHeight / 2);
    }

    // Mark as programmatic move to prevent viewport change callback
    // Reset flag after moveend completes (use a timeout to ensure it happens after the event)
    isProgrammaticMoveRef.current = true;
    
    // Set up a one-time moveend handler to reset the flag after the programmatic move completes
    const resetFlag = () => {
      isProgrammaticMoveRef.current = false;
      map.off("moveend", resetFlag);
    };
    map.once("moveend", resetFlag);
    
    map.easeTo({
      center: [loc.lng, loc.lat],
      zoom: Math.max(map.getZoom(), 14),
      duration: 900,
      essential: true,
      offset: [0, offsetY],
    });

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
      // When the user closes the popup, treat it like a background tap (deselect)
      try {
        popup.on("close", () => { try { onMapClick?.(); } catch { } });
      } catch { }
      popupRef.current = popup;
    } catch { }
  }, [selectedId, mapReady, locations, bottomSheetHeight]);

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

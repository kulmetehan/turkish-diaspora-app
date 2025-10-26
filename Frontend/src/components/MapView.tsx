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
  bottomSheetHeight?: number;
};

/**
 * MapView: toont de Mapbox-kaart en de MarkerLayer.
 * - Houdt één map-instantie in leven
 * - Centreert vloeiend op geselecteerde locatie
 */
export default function MapView({ locations, selectedId, onSelect, onMapClick, bottomSheetHeight }: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const popupRef = useRef<mapboxgl.Popup | null>(null);

  // Init Map slechts één keer
  useEffect(() => {
    if (mapRef.current || !mapContainerRef.current) return;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: import.meta.env.VITE_MAPBOX_STYLE || "mapbox://styles/mapbox/streets-v12",
      center: [4.4777, 51.9244], // Rotterdam default
      zoom: 11,
      attributionControl: false,
    });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => setMapReady(true));

    // Add map click handler (robust hit test: only treat as background click when no featured hit)
    map.on("click", (e) => {
      if (!onMapClick) return;
      try {
        const feats = map.queryRenderedFeatures(e.point);
        const hit = Array.isArray(feats) && feats.some((f: any) => f?.source === "tda-locations");
        if (hit) return; // let layer-specific handlers handle marker/cluster clicks
      } catch { /* ignore */ }
      onMapClick();
    });

    mapRef.current = map;

    return () => {
      try {
        map.remove();
      } catch { }
      mapRef.current = null;
    };
  }, []);

  // Vloeiend centreren bij klik op lijst-item
  useEffect(() => {
    if (!mapReady || !locations?.length) return;
    const map = mapRef.current;
    if (!map) return;

    // If deselected → remove popup (if any) and bail
    if (!selectedId) {
      try { popupRef.current?.remove(); } catch { }
      popupRef.current = null;
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

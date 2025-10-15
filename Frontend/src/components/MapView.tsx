// Frontend/src/components/MapView.tsx

// Zorg dat Leaflet CSS geladen is (defensieve extra import; dubbel importen is onschadelijk in Vite)
import "leaflet/dist/leaflet.css";

import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import L from "leaflet";

import type { Location } from "../types/location";
import { useSelectedLocationId, selectLocation } from "../state/ui";

type Props = {
  locations: Location[];
};

// --- Leaflet default icon fix ---
const DefaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  tooltipAnchor: [16, -28],
  shadowSize: [41, 41],
});

const SelectedIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [30, 49],
  iconAnchor: [15, 49],
  popupAnchor: [1, -40],
  tooltipAnchor: [16, -35],
  shadowSize: [49, 49],
  className: "leaflet-marker-selected",
});

L.Marker.prototype.options.icon = DefaultIcon;

function SelectedMarkerFollower({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.panTo([lat, lng], { animate: true });
  }, [lat, lng, map]);
  return null;
}

export default function MapView({ locations }: Props) {
  const selectedId = useSelectedLocationId();

  const selectedLoc = useMemo(
    () => locations.find((l) => l.id === selectedId) ?? null,
    [locations, selectedId]
  );

  const initialCenter: LatLngExpression = selectedLoc
    ? ([selectedLoc.lat, selectedLoc.lng] as LatLngExpression)
    : ([51.9225, 4.47917] as LatLngExpression); // Rotterdam fallback

  // Bewaar directe Leaflet marker instanties
  const markerRefs = useRef<Record<string, L.Marker | null>>({});

  // Open popup van de geselecteerde marker wanneer de selectie wijzigt
  useEffect(() => {
    if (!selectedId) return;
    const m = markerRefs.current[selectedId];
    if (m) m.openPopup();
  }, [selectedId]);

  if (!locations.length) {
    return <div style={{ padding: 8 }}>Geen locaties om te tonen.</div>;
  }

  return (
    <MapContainer center={initialCenter} zoom={12} style={{ width: "100%", height: "100vh" }}>
      <TileLayer
        attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {selectedLoc && <SelectedMarkerFollower lat={selectedLoc.lat} lng={selectedLoc.lng} />}

      {locations.map((loc) => {
        const isSelected = loc.id === selectedId;
        return (
          <Marker
            key={loc.id}
            position={[loc.lat, loc.lng]}
            icon={isSelected ? SelectedIcon : DefaultIcon}
            ref={(instance) => {
              markerRefs.current[loc.id] = instance;
            }}
            eventHandlers={{
              click: () => selectLocation(loc.id),
            }}
          >
            <Popup>
              <strong>{loc.name}</strong>
              <br />
              {loc.address ?? "—"}
              <br />
              {loc.category ?? "—"}
              {typeof loc.rating === "number" ? (
                <>
                  <br />
                  {loc.rating.toFixed(1)} ★{loc.user_ratings_total ? ` (${loc.user_ratings_total})` : ""}
                </>
              ) : null}
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}

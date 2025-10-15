import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { LatLngExpression } from "leaflet";

import { getLocations } from "../lib/api";
import type { Location } from "../types/location";
import { NL_CENTER, NL_ZOOM } from "../lib/geo";
import { useUserPosition } from "../hooks/useUserPosition";

// Fix default marker icons in Vite so Leaflet pins render correctly
import marker2x from "leaflet/dist/images/marker-icon-2x.png";
import marker1x from "leaflet/dist/images/marker-icon.png";
import shadow from "leaflet/dist/images/marker-shadow.png";
L.Icon.Default.mergeOptions({
  iconRetinaUrl: marker2x,
  iconUrl: marker1x,
  shadowUrl: shadow,
});

function FlyTo({ center }: { center: LatLngExpression }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 12, { duration: 0.8 });
  }, [center, map]);
  return null;
}

export default function MapView() {
  const { coords, status } = useUserPosition(6000);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [items, setItems] = useState<Location[]>([]);
  const [center, setCenter] = useState<LatLngExpression>([
    NL_CENTER.lat,
    NL_CENTER.lng,
  ]);

  // Center on user if permission is granted
  useEffect(() => {
    if (status === "granted" && coords) {
      setCenter([coords.lat, coords.lng]);
    }
  }, [status, coords]);

  // Load locations
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);

    getLocations({ limit: 200 })
      .then((data) => {
        if (cancelled) return;
        setItems(data);
      })
      .catch((e) => {
        if (cancelled) return;
        setErr(e?.message || "Kon locaties niet laden.");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const markers = useMemo(() => items, [items]);

  return (
    <div className="map-root">{/* height is controlled in index.css */}
      <MapContainer
        center={center}
        zoom={NL_ZOOM}
        preferCanvas
        worldCopyJump
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {Array.isArray(center) && status === "granted" && (
          <FlyTo center={center} />
        )}

        {markers.map((loc) => (
          <Marker key={loc.id} position={[loc.lat, loc.lng]}>
            <Popup>
              <div style={{ minWidth: 180 }}>
                <strong>{loc.name}</strong>
                <div style={{ fontSize: 12, opacity: 0.8 }}>
                  {loc.category || "other"}
                </div>
                {loc.address && (
                  <div style={{ fontSize: 12, marginTop: 4 }}>{loc.address}</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Lightweight status toasts */}
      {loading && (
        <div
          className="pointer-events-none"
          style={{
            position: "absolute",
            left: "50%",
            top: 12,
            transform: "translateX(-50%)",
            zIndex: 1000,
            background: "rgba(255,255,255,0.9)",
            padding: "4px 8px",
            borderRadius: 6,
            fontSize: 13,
            boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
          }}
        >
          Locaties laden…
        </div>
      )}
      {err && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: 12,
            transform: "translateX(-50%)",
            zIndex: 1000,
            background: "#dc2626",
            color: "white",
            padding: "4px 8px",
            borderRadius: 6,
            fontSize: 13,
            boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
          }}
        >
          {err}
        </div>
      )}
    </div>
  );
}

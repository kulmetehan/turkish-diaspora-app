// Frontend/src/hooks/useLocations.ts
//
// - Werkt met Vite proxy (/api -> backend) OF met VITE_API_BASE als je die zet.
// - Gooit een duidelijke fout als response geen JSON is (content-type check).

import { useEffect, useMemo, useRef, useState } from "react";
import type { Location, LocationList } from "../types/location";
import { useUserPosition } from "../hooks/useUserPosition";

// --- helpers ---

function buildUrl(): string {
  // Als je VITE_API_BASE zet, gebruiken we die, anders de /api proxy.
  const base =
    (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE) || "";
  const trimmed = typeof base === "string" ? base.replace(/\/+$/, "") : "";
  if (trimmed) return `${trimmed}/api/v1/locations`;
  return `/api/v1/locations`; // via Vite proxy
}

function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const toRad = (x: number) => (x * Math.PI) / 180;
  const R = 6371; // km
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const s1 =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(s1), Math.sqrt(1 - s1));
  return R * c;
}

// --- hook ---

export function useLocations() {
  const [raw, setRaw] = useState<LocationList>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const userPos = useUserPosition(); // { status, coords: {lat,lng} | null, error }
  const lastPosRef = useRef<{ lat: number; lng: number } | null>(null);

  // Initial fetch
  useEffect(() => {
    let aborted = false;
    const url = `/api/v1/locations/?only_turkish=true&limit=200`;

    (async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(url, { method: "GET" });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} @ ${url}`);
        }

        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
          const text = await res.text().catch(() => "");
          throw new Error(
            `Expected JSON but got "${ct || "unknown"}" @ ${url}. Snippet: ${text.slice(0, 120)}`
          );
        }

        const data: LocationList = await res.json();

        if (!aborted) {
          setRaw(
            data
              .filter(
                (d) =>
                  d &&
                  typeof d.lat === "number" &&
                  typeof d.lng === "number" &&
                  typeof d.name === "string" &&
                  typeof d.id !== "undefined"
              )
              .map((d) => ({
                ...d,
                id: String((d as any).id), // normaliseer naar string
              }))
          );
        }
      } catch (e: any) {
        if (!aborted) setError(e?.message ?? "Unknown error");
      } finally {
        if (!aborted) setLoading(false);
      }
    })();

    return () => {
      aborted = true;
    };
  }, []);

  // Enrich met distance wanneer coords beschikbaar zijn
  const withDistance: LocationList = useMemo(() => {
    const coords = userPos?.coords ?? null;
    if (!coords) return raw;

    const pos = { lat: coords.lat, lng: coords.lng };
    lastPosRef.current = pos;

    return raw.map((l) => {
      const km = haversineKm(pos.lat, pos.lng, l.lat, l.lng);
      return { ...l, distanceKm: km };
    });
  }, [raw, userPos?.coords?.lat, userPos?.coords?.lng]);

  // Unieke categorieën (gesorteerd)
  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const l of raw) {
      if (l.category && l.category.trim()) set.add(l.category.trim());
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [raw]);

  return {
    locations: withDistance,
    categories,
    isLoading: loading,
    error,
  };
}

export type UseLocationsReturn = ReturnType<typeof useLocations>;

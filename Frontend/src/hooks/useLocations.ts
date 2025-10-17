// Frontend/src/hooks/useLocations.ts
//
// - Werkt in DEV via Vite proxy (/api -> backend).
// - Werkt in PROD (GitHub Pages) via absolute base uit VITE_API_BASE_URL.
// - Haalt VERIFIED records op (limit 200) ivm <2s 3G-doel.
// - Houdt jouw bestaande return shape aan: { locations, categories, isLoading, error }.

import { useEffect, useMemo, useRef, useState } from "react";
import type { Location, LocationList } from "../types/location";
import { useUserPosition } from "../hooks/useUserPosition";

/** Bepaal de API base:
 *  - PROD (Pages): .env.production bevat VITE_API_BASE_URL (gezet door CI).
 *  - DEV: geen VITE_API_BASE_URL => we vallen terug op de Vite proxy met relatieve /api.
 */
function getApiBase(): string {
  const fromEnv = (import.meta as any)?.env?.VITE_API_BASE_URL as string | undefined;
  if (fromEnv && typeof fromEnv === "string" && fromEnv.trim()) {
    return fromEnv.replace(/\/+$/, ""); // trim trailing slashes
  }
  return ""; // dev proxy
}

/** Bouw de fetch-URL (VERIFIED + limit) */
function buildUrl(limit = 200): string {
  const fromEnv = (import.meta as any)?.env?.VITE_API_BASE_URL as string | undefined;
  const base = (fromEnv && fromEnv.trim()) ? fromEnv.replace(/\/+$/, "") : ""; // no trailing slash

  // IMPORTANT: always hit the trailing-slash endpoint to avoid 307/308 redirect
  const prefix = base ? `${base}/api` : "/api";      // prod absolute vs. dev proxy
  const path = `${prefix}/v1/locations/`;            // <-- trailing slash here

  const url = new URL(path, window.location.origin);
  url.searchParams.set("state", "VERIFIED");
  url.searchParams.set("limit", String(limit));
  // url.searchParams.set("only_turkish", "true"); // enable if your API supports it

  // In dev (relative path), return path+query only; in prod return full URL
  return base ? url.toString() : `${url.pathname}${url.search}`;
}

/** Afstand in km (voor enrichment) */
function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const toRad = (x: number) => (x * Math.PI) / 180;
  const R = 6371; // km
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const s1 =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(s1), Math.sqrt(1 - s1));
  return R * c;
}

export function useLocations(limit = 200) {
  // Hou types in gebruik zodat TS geen unused warnings geeft
  const [_typeGuardLocation] = useState<Location | null>(null);

  const [raw, setRaw] = useState<LocationList>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const userPos = useUserPosition(); // { status, coords: {lat,lng} | null, error }
  const lastPosRef = useRef<{ lat: number; lng: number } | null>(null);

  // Initial fetch
  useEffect(() => {
    let aborted = false;
    const url = buildUrl(limit);

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

        // Backend kan array of {items}/{data} teruggeven; normaliseer naar array
        const json = await res.json();
        const list: unknown =
          (Array.isArray(json) && json) ||
          (Array.isArray(json?.items) && json.items) ||
          (Array.isArray(json?.data) && json.data) ||
          [];

        const safe: LocationList = (list as LocationList)
          .filter(
            (d) =>
              d &&
              typeof d.lat === "number" &&
              typeof d.lng === "number" &&
              typeof d.name === "string" &&
              typeof (d as any).id !== "undefined"
          )
          .map((d) => ({
            ...d,
            id: String((d as any).id), // normaliseer id naar string
          }));

        if (!aborted) setRaw(safe);
      } catch (e: any) {
        if (!aborted) setError(e?.message ?? "Unknown error");
      } finally {
        if (!aborted) setLoading(false);
      }
    })();

    return () => {
      aborted = true;
    };
  }, [limit]);

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

  // Houd de exact verwachte return shape aan voor App.tsx:
  return {
    locations: withDistance,
    categories,
    isLoading: loading,
    error,
  };
}

export type UseLocationsReturn = ReturnType<typeof useLocations>;

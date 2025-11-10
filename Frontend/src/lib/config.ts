// Frontend/src/lib/config.ts
// Normaliseer API_BASE_URL zó dat hij altijd op /api/v1 eindigt.
// Zo voorkom je fouten wanneer .env per ongeluk alleen de host bevat.

function normalizeApiBase(raw: string | undefined): string {
  // default naar /api/v1 (relative) zodat dev-proxy ook nog kan
  const base = (raw ?? "/api/v1").replace(/\/+$/, ""); // strip trailing slashes
  if (base.endsWith("/api/v1")) return base;
  return `${base}/api/v1`;
}

export const CONFIG = {
  API_BASE_URL: normalizeApiBase(import.meta.env.VITE_API_BASE_URL as string | undefined),

  MAPBOX_TOKEN: (import.meta.env.VITE_MAPBOX_TOKEN as string | undefined) ?? "pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw",
  MAPBOX_STYLE:
    (import.meta.env.VITE_MAPBOX_STYLE as string | undefined) ??
    "mapbox://styles/mapbox/light-v11",

  MAP_MIN_ZOOM: 3,
  MAP_MAX_ZOOM: 19,
  MAP_DEFAULT: {
    lat: 51.9244, // Rotterdam
    lng: 4.4777,
    zoom: 11,
  },
  MAP_MY_LOCATION_ZOOM: 14,

  CACHE_TTL_MS: 60_000,
  FETCH_DEBOUNCE_MS: 300,
} as const;

export type BBox = { west: number; south: number; east: number; north: number };

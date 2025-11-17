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
    "mapbox://styles/mapbox/streets-v12",

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

export const CLUSTER_CONFIG = {
  MAX_ZOOM: 15, // Increased from 14 to show more individual markers at district-level zoom
  RADIUS: 30, // Reduced from 50 for less aggressive clustering
  MOBILE_MAX_ZOOM: 16, // Mobile devices can handle slightly higher zoom before clustering stops
  MOBILE_RADIUS_MULTIPLIER: 0.8, // Mobile uses 80% of desktop radius for better clarity
} as const;

export type BBox = { west: number; south: number; east: number; north: number };

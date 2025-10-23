// src/lib/api/location.ts
import { API_BASE, apiFetch } from '../api';

/**
 * Basis type voor een locatie-item zoals de frontend het gebruikt.
 * Houd het klein en stabiel; alles wat de UI nodig heeft zit hierin.
 */
export type Location = {
  id: number;
  name: string;
  lat: number;
  lng: number;
  category?: string | null;
  state?: string | null;
  rating?: number | null;
  confidence_score?: number | null;
  is_turkish?: boolean | null;
};

/**
 * Normaliseert ruwe API-data naar ons Location-type.
 * - forceert id → number
 * - forceert lat/lng → number
 */
export function normalizeLocation(raw: any): Location {
  return {
    id: typeof raw?.id === "string" ? parseInt(raw.id, 10) : Number(raw?.id),
    name: raw?.name ?? "",
    lat: Number(raw?.lat),
    lng: Number(raw?.lng),
    category: raw?.category ?? null,
    state: raw?.state ?? null,
    rating: raw?.rating ?? null,
    confidence_score: raw?.confidence_score ?? null,
    is_turkish: raw?.is_turkish ?? null,
  };
}

/**
 * Bouwt de URL voor het backend endpoint.
 * Je kunt filters hier later uitbreiden zonder alle call-sites te wijzigen.
 */
function buildLocationsUrl() {
  // Return relative path - apiFetch will prepend API_BASE
  const params = new URLSearchParams({
    state: "VERIFIED",
    limit: "1000",
    // Vraag alleen velden op die we gebruiken → minder payload & sneller
    fields: [
      "id",
      "name",
      "lat",
      "lng",
      "category",
      "state",
      "rating",
      "confidence_score",
      "is_turkish",
    ].join(","),
  });
  const url = `/locations/?${params.toString()}`;
  console.log('buildLocationsUrl constructed:', { API_BASE, url });
  return url;
}

/**
 * Haalt locaties op en normaliseert ze.
 * Backend kan array of {results: []} teruggeven — beide worden ondersteund.
 */
export async function fetchLocations(): Promise<Location[]> {
  const url = buildLocationsUrl();
  const json = await apiFetch<any>(url);

  const list: any[] = Array.isArray(json) ? json : Array.isArray(json?.results) ? json.results : [];
  return list.map(normalizeLocation).filter((l) => Number.isFinite(l.id) && Number.isFinite(l.lat) && Number.isFinite(l.lng));
}

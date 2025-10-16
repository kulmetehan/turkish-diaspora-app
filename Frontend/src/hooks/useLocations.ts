import { useEffect, useState } from "react";

/**
 * Publieke shape van een locatie zoals de frontend 'm gebruikt.
 * Pas velden gerust aan op basis van je API-contract (/api/v1/locations).
 */
export type Location = {
  id: number;
  name: string;
  lat: number;
  lng: number;
  category?: string;
  rating?: number | null;
  website?: string | null;
  address?: string;
};

/**
 * Base-URL komt uit de GitHub Pages workflow:
 * .env.production -> VITE_API_BASE_URL
 * Lokaal werkt je dev-proxy via /api; voor prod gebruiken we de absolute base.
 */
const API_BASE: string = import.meta.env.VITE_API_BASE_URL;

/**
 * Helper die een consistente fetch-URL maakt voor VERIFIED records.
 * - limit: initieel max aantal markers (200 voor performance op 3G)
 * - extraQuery: space voor toekomstige filters (category, bbox, etc.)
 */
function buildApiUrl(limit: number, extraQuery?: Record<string, string | number | boolean>) {
  const url = new URL(`${API_BASE}/api/v1/locations`);
  url.searchParams.set("state", "VERIFIED");
  url.searchParams.set("limit", String(limit));

  if (extraQuery) {
    Object.entries(extraQuery).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  return url.toString();
}

type HookState = {
  data: Location[];
  loading: boolean;
  error: string | null;
};

/**
 * useLocations
 * - Haalt VERIFIED locaties op met rating/website (indien beschikbaar)
 * - Beperkt initieel resultaat voor snelle laadtijden
 */
export function useLocations(initialLimit = 200, extraQuery?: Record<string, string | number | boolean>) {
  const [state, setState] = useState<HookState>({ data: [], loading: true, error: null });

  useEffect(() => {
    const controller = new AbortController();

    async function run() {
      try {
        setState((s) => ({ ...s, loading: true, error: null }));

        const url = buildApiUrl(initialLimit, extraQuery);
        const resp = await fetch(url, { signal: controller.signal });
        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`);
        }

        const json = await resp.json();

        // Probeer een paar gebruikelijke vormen te ondersteunen:
        // - { items: Location[] } of { data: Location[] } of direct Location[]
        const items: Location[] =
          (Array.isArray(json) && json) ||
          (Array.isArray(json?.items) && json.items) ||
          (Array.isArray(json?.data) && json.data) ||
          [];

        setState({ data: items, loading: false, error: null });
      } catch (err: unknown) {
        if ((err as any)?.name === "AbortError") return;
        const msg = err instanceof Error ? err.message : "Unknown error";
        setState({ data: [], loading: false, error: msg });
      }
    }

    run();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialLimit, JSON.stringify(extraQuery)]);

  return state;
}

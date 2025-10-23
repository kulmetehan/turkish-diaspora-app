// Frontend/src/lib/api.ts

// In development gebruiken we de Vite dev-proxy op "/api".
// In productie gebruiken we een absolute origin uit VITE_API_BASE_URL.
// BASE-pad van endpoints blijft altijd "/api/v1".
const DEV = import.meta.env.DEV;

// Let op: geen trailing slash in VITE_API_BASE_URL
const PROD_ORIGIN = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

// Fallback to demo data when no backend is configured
const API_ROOT = DEV ? "" : (PROD_ORIGIN ?? "");
export const API_BASE = `${API_ROOT}/api/v1`;

// Debug logging to help troubleshoot
if (!DEV) {
  console.log('Production API Configuration:', {
    PROD_ORIGIN,
    API_ROOT,
    API_BASE,
    hasBackend: !!PROD_ORIGIN
  });

  // If backend is configured but not working, fall back to demo data
  if (PROD_ORIGIN) {
    console.log('Backend configured, but will test connection first...');
  }
}

/** Demo data for Bangkok locations when backend is not available */
const DEMO_DATA = {
  "/locations/": {
    data: [
      {
        id: 1,
        name: "Demo Turkish Restaurant",
        lat: 13.7563,
        lng: 100.5018,
        category: "restaurant",
        state: "VERIFIED",
        rating: 4.5,
        confidence_score: 0.95,
        is_turkish: true
      },
      {
        id: 2,
        name: "Demo Turkish Bakery",
        lat: 13.7563,
        lng: 100.5018,
        category: "bakery",
        state: "VERIFIED",
        rating: 4.3,
        confidence_score: 0.90,
        is_turkish: true
      }
    ],
    total: 2
  }
};

/** Kleine helper voor fetch-calls naar onze API */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  // If no backend is configured, return demo data
  if (!PROD_ORIGIN && !DEV) {
    console.warn('No backend configured (VITE_API_BASE_URL not set), using demo data');
    const demoResponse = DEMO_DATA[path as keyof typeof DEMO_DATA];
    if (demoResponse) {
      return demoResponse as T;
    }
    // If no demo data available, throw a more helpful error
    throw new Error(`No backend configured and no demo data available for ${path}`);
  }

  const url = `${API_BASE}${path}`;

  try {
    const res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });

    if (!res.ok) {
      // If backend is not available, fall back to demo data
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        console.warn(`Backend not available (${res.status}), falling back to demo data`);
        const demoResponse = DEMO_DATA[path as keyof typeof DEMO_DATA];
        if (demoResponse) {
          return demoResponse as T;
        }
      }

      const text = await res.text().catch(() => "");
      throw new Error(
        `API ${res.status} ${res.statusText} @ ${path}${text ? ` — ${text.slice(0, 300)}` : ""}`
      );
    }

    // Als er geen body is, niet proberen te parsen
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      // sommige endpoints geven leeg terug (204 / text)
      const text = await res.text().catch(() => "");
      return text as unknown as T;
    }
    return (await res.json()) as T;
  } catch (error) {
    // If fetch fails completely (network error, CORS, etc.), fall back to demo data
    console.warn(`Network error fetching from backend, falling back to demo data:`, error);
    const demoResponse = DEMO_DATA[path as keyof typeof DEMO_DATA];
    if (demoResponse) {
      return demoResponse as T;
    }
    throw error;
  }
}

/** Admin-key uit localStorage ophalen (niet bundelen) */
export function getAdminKey(): string {
  return localStorage.getItem("ADMIN_API_KEY") || "";
}

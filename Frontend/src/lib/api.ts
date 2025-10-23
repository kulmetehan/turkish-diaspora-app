// Frontend/src/lib/api.ts

// In development gebruiken we de Vite dev-proxy op "/api".
// In productie gebruiken we een absolute origin uit VITE_API_BASE_URL.
// BASE-pad van endpoints blijft altijd "/api/v1".
const DEV = import.meta.env.DEV;

// Let op: geen trailing slash in VITE_API_BASE_URL
const PROD_ORIGIN = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

// Fallback to dev proxy in development, absolute origin in production
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
  // In production, require a configured backend
  if (!DEV && !PROD_ORIGIN) {
    throw new Error('Backend not configured (VITE_API_BASE_URL not set)');
  }

  const url = `${API_BASE}${path}`;

  // Simple retry/backoff for cold starts or transient failures
  const maxAttempts = 3;
  const delays = [500, 1500]; // ms between attempts (after first failure)

  let lastError: unknown = null;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        ...init,
      });

      if (!res.ok) {
        // Retry on typical warm-up statuses
        if (res.status === 502 || res.status === 503 || res.status === 504) {
          const text = await res.text().catch(() => "");
          lastError = new Error(
            `API ${res.status} ${res.statusText} @ ${path}${text ? ` — ${text.slice(0, 300)}` : ""}`
          );
          // fall through to retry logic
        } else {
          const text = await res.text().catch(() => "");
          throw new Error(
            `API ${res.status} ${res.statusText} @ ${path}${text ? ` — ${text.slice(0, 300)}` : ""}`
          );
        }
      } else {
        // Als er geen body is, niet proberen te parsen
        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
          const text = await res.text().catch(() => "");
          return text as unknown as T;
        }
        return (await res.json()) as T;
      }
    } catch (err) {
      // Network/CORS/etc.
      lastError = err;
    }

    if (attempt < maxAttempts) {
      const wait = delays[attempt - 1] ?? 1500;
      await new Promise((r) => setTimeout(r, wait));
    }
  }

  // Development-only demo fallback to keep local UI usable when backend missing
  if (DEV) {
    const demoResponse = DEMO_DATA[path as keyof typeof DEMO_DATA];
    if (demoResponse) return demoResponse as T;
  }

  throw (lastError ?? new Error('Failed to fetch API'));
}

/** Admin-key uit localStorage ophalen (niet bundelen) */
export function getAdminKey(): string {
  return localStorage.getItem("ADMIN_API_KEY") || "";
}

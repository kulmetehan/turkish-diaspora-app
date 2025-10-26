// Frontend/src/lib/api.ts
import { supabase } from "@/lib/supabaseClient";

// Always use explicit API base from env; must include /api/v1
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

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
  // Require a configured backend in all modes
  if (!API_BASE) {
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
        if (res.status === 401 || res.status === 403) {
          try { await supabase.auth.signOut(); } catch { }
        }
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
        // Alleen JSON is geldig; non-JSON behandelen als fout (bv. warm-up HTML)
        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
          throw new Error(`Invalid response content-type for ${path}: ${ct || "<none>"} @ ${url}`);
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

export async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not authenticated");
  if (import.meta.env.DEV) {
    // Helpful during local debugging
    // eslint-disable-next-line no-console
    console.debug("authFetch →", `${API_BASE}${path}`);
  }
  return apiFetch<T>(path, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function whoAmI(): Promise<{ ok: boolean; admin_email: string }> {
  return authFetch("/admin/whoami");
}

// Frontend/src/lib/api.ts

// In development gebruiken we de Vite dev-proxy op "/api".
// In productie gebruiken we een absolute origin uit VITE_API_BASE_URL.
// BASE-pad van endpoints blijft altijd "/api/v1".
const DEV = import.meta.env.DEV;

// Let op: geen trailing slash in VITE_API_BASE_URL
const PROD_ORIGIN = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

const API_ROOT = DEV ? "" : (PROD_ORIGIN ?? "");
export const API_BASE = `${API_ROOT}/api/v1`;

/** Kleine helper voor fetch-calls naar onze API */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
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
}

/** Admin-key uit localStorage ophalen (niet bundelen) */
export function getAdminKey(): string {
  return localStorage.getItem("ADMIN_API_KEY") || "";
}

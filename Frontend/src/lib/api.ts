// Frontend/src/lib/api.ts
import type { Location } from "../types/location";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

if (!API_BASE_URL) {
  // Valt op tijdens dev als je .env mist
  // (console.warn is genoeg; we willen geen crash)
  console.warn('VITE_API_BASE_URL is not set in your environment files.');
}

export async function getHealth(): Promise<{ status: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/healthz`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function getLocations(params?: {
  lat?: number;
  lng?: number;
  radius?: number;
  category?: string[]; // multi
  limit?: number;
}): Promise<Location[]> {
  const usp = new URLSearchParams();
  if (params?.lat != null) usp.set("lat", String(params.lat));
  if (params?.lng != null) usp.set("lng", String(params.lng));
  if (params?.radius != null) usp.set("radius", String(params.radius));
  if (params?.limit != null) usp.set("limit", String(params.limit));
  if (params?.category && params.category.length) {
    params.category.forEach((c) => usp.append("category", c));
  }

  const url = `${API_BASE_URL}/api/v1/locations${usp.toString() ? `?${usp}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET /locations failed ${res.status}: ${text}`);
  }
  return (await res.json()) as Location[];
}
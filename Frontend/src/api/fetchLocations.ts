// src/api/fetchLocations.ts
import { getAcceptLanguageHeader } from "@/i18n";

export interface CategoryOption {
    key: string;
    label: string;
}

export interface LocationMarker {
    id: string;
    name: string;
    lat: number | null;
    lng: number | null;
    // Optional address & identifiers
    address?: string | null;
    place_id?: string | null;
    city?: string | null;
    // Raw category from DB (still returned by backend)
    category: string;
    // Canonicalized category fields from backend
    category_raw?: string;
    category_key?: string;
    category_label?: string;
    state: string;
    // rating is legacy (Google). The frontend does not display or use it.
    rating: number | null;
    confidence_score: number | null;
    is_turkish: boolean;
}

export async function fetchLocations(
    bbox?: string | null,
    limit?: number,
    offset?: number,
    signal?: AbortSignal
): Promise<LocationMarker[]> {
    const fallbackBase = "http://127.0.0.1:8000";
    const envBase = (import.meta as any)?.env?.VITE_API_BASE_URL;
    const API_BASE = (typeof envBase === "string" && envBase.length > 0) ? envBase : fallbackBase;

    // Build query string
    const params = new URLSearchParams();
    if (bbox && bbox.trim()) {
        params.append("bbox", bbox.trim());
    }
    if (limit !== undefined && limit > 0) {
        params.append("limit", String(limit));
    }
    if (offset !== undefined && offset >= 0) {
        params.append("offset", String(offset));
    }

    const queryString = params.toString();
    const url = `${API_BASE}/api/v1/locations${queryString ? `?${queryString}` : ""}`;

    const resp = await fetch(url, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Accept-Language": getAcceptLanguageHeader(),
        },
        signal,
    });
    if (!resp.ok) {
        throw new Error(`Failed to load locations: ${resp.status} ${resp.statusText}`);
    }

    const raw = await resp.json();

    return (Array.isArray(raw) ? raw : []).map((loc: any): LocationMarker => {
        const conf = typeof loc?.confidence_score === "number"
            ? loc.confidence_score
            : (loc?.confidence_score ? Number(loc.confidence_score) : 0);
        const st = String(loc?.state ?? "CANDIDATE");

        const isVisibleByHeuristic = (
            (st === "VERIFIED" && conf >= 0.8) ||
            ((st === "PENDING_VERIFICATION" || st === "CANDIDATE") && conf >= 0.9)
        );

        return {
            id: String(loc?.id ?? ""),
            name: String(loc?.name ?? "Unknown"),
            lat: typeof loc?.lat === "number" ? loc.lat : null,
            lng: typeof loc?.lng === "number" ? loc.lng : null,
            address: typeof loc?.address === "string" ? loc.address : null,
            place_id: typeof loc?.place_id === "string" ? loc.place_id : undefined,
            city: typeof loc?.city === "string" ? loc.city : undefined,
            category: String(loc?.category ?? "other"),
            category_raw: (typeof loc?.category_raw === "string" ? loc.category_raw : String(loc?.category ?? "")) || undefined,
            category_key: typeof loc?.category_key === "string" ? loc.category_key : undefined,
            category_label: typeof loc?.category_label === "string" ? loc.category_label : undefined,
            state: st,
            rating: (typeof loc?.rating === "number" ? loc.rating : (loc?.rating ? Number(loc.rating) : null)) ?? null,
            confidence_score: Number.isFinite(conf) ? conf : null,
            is_turkish: isVisibleByHeuristic,
        };
    });
}

export async function fetchLocationsCount(bbox?: string | null, signal?: AbortSignal): Promise<number> {
    const fallbackBase = "http://127.0.0.1:8000";
    const envBase = (import.meta as any)?.env?.VITE_API_BASE_URL;
    const API_BASE = (typeof envBase === "string" && envBase.length > 0) ? envBase : fallbackBase;

    // Build query string
    const params = new URLSearchParams();
    if (bbox && bbox.trim()) {
        params.append("bbox", bbox.trim());
    }

    const queryString = params.toString();
    const url = `${API_BASE}/api/v1/locations/count${queryString ? `?${queryString}` : ""}`;

    const resp = await fetch(url, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Accept-Language": getAcceptLanguageHeader(),
        },
        signal,
    });
    if (!resp.ok) {
        throw new Error(`Failed to load location count: ${resp.status} ${resp.statusText}`);
    }

    const data = await resp.json();
    return typeof data.count === "number" ? data.count : 0;
}

export async function fetchCategories(signal?: AbortSignal): Promise<CategoryOption[]> {
    const fallbackBase = "http://127.0.0.1:8000";
    const envBase = (import.meta as any)?.env?.VITE_API_BASE_URL;
    const API_BASE = (typeof envBase === "string" && envBase.length > 0) ? envBase : fallbackBase;

    // Use new categories endpoint
    const url = `${API_BASE}/api/v1/categories`;

    const resp = await fetch(url, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Accept-Language": getAcceptLanguageHeader(),
        },
        signal,
    });

    if (!resp.ok) {
        throw new Error(`Failed to load categories: ${resp.status} ${resp.statusText}`);
    }

    const data = await resp.json();
    return (Array.isArray(data) ? data : []).map((c: any) => ({
        key: String(c.key ?? "").toLowerCase().trim(),
        label: String(c.label ?? c.key ?? "").trim() || String(c.key ?? "").trim(),
    })).filter((c) => c.key && c.key !== "other");
}



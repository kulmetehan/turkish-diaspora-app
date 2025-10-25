// src/api/fetchLocations.ts
export interface LocationMarker {
    id: string;
    name: string;
    lat: number | null;
    lng: number | null;
    category: string;
    state: string;
    // rating is legacy (Google). The frontend does not display or use it.
    rating: number | null;
    confidence_score: number | null;
    is_turkish: boolean;
}

export async function fetchLocations(): Promise<LocationMarker[]> {
    const fallbackBase = "http://127.0.0.1:8000";
    const envBase = (import.meta as any)?.env?.VITE_API_BASE_URL;
    const API_BASE = (typeof envBase === "string" && envBase.length > 0) ? envBase : fallbackBase;

    const resp = await fetch(`${API_BASE}/api/v1/locations`, {
        method: "GET",
        headers: {
            "Accept": "application/json",
        },
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
            category: String(loc?.category ?? "other"),
            state: st,
            rating: (typeof loc?.rating === "number" ? loc.rating : (loc?.rating ? Number(loc.rating) : null)) ?? null,
            confidence_score: Number.isFinite(conf) ? conf : null,
            is_turkish: isVisibleByHeuristic,
        };
    });
}



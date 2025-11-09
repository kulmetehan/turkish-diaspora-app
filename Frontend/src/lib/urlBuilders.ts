import type { LocationMarker } from "@/api/fetchLocations";

const GOOGLE_MAPS_DIRECTIONS_BASE = "https://www.google.com/maps/dir/";
const GOOGLE_SEARCH_BASE = "https://www.google.com/search";
const DEFAULT_CITY_FALLBACK = "Rotterdam";

function resolveUserAgent(explicitUa?: string): string {
    if (explicitUa) return explicitUa;
    if (typeof navigator !== "undefined" && typeof navigator.userAgent === "string") {
        return navigator.userAgent;
    }
    return "";
}

function isIos(userAgent?: string): boolean {
    const ua = resolveUserAgent(userAgent);
    return /\b(iPad|iPhone|iPod)\b/i.test(ua);
}

function isAndroid(userAgent?: string): boolean {
    const ua = resolveUserAgent(userAgent);
    return /\bAndroid\b/i.test(ua);
}

function hasCoordinates(location: LocationMarker): location is LocationMarker & { lat: number; lng: number } {
    return typeof location.lat === "number" && Number.isFinite(location.lat) &&
        typeof location.lng === "number" && Number.isFinite(location.lng);
}

function parseCityFromAddress(address?: string | null): string | null {
    if (!address) return null;
    const segments = address
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
    for (let i = segments.length - 1; i >= 0; i -= 1) {
        let candidate = segments[i];
        // Strip postal codes like "3011 AB" or "3011AB"
        candidate = candidate.replace(/\b\d{4}\s?[A-Z]{2}\b/gi, "").trim();
        if (!candidate) continue;
        // Remove country names to avoid returning them as city
        if (/^(netherlands|nederland|the netherlands)$/i.test(candidate)) {
            continue;
        }
        if (/[a-zA-Z]/.test(candidate)) {
            return candidate;
        }
    }
    return null;
}

export function deriveCityForLocation(location: Pick<LocationMarker, "address" | "city">, fallback = DEFAULT_CITY_FALLBACK): string {
    const direct = typeof location.city === "string" && location.city.trim().length > 0
        ? location.city.trim()
        : null;
    const parsed = direct ?? parseCityFromAddress(location.address);
    if (parsed && parsed.trim().length > 0) {
        return parsed.trim();
    }
    return fallback;
}

export function buildRouteUrl(location: LocationMarker, userAgent?: string): string {
    const ua = resolveUserAgent(userAgent);
    const coordsAvailable = hasCoordinates(location);
    const encodedName = encodeURIComponent(location.name ?? "");

    if (isIos(ua)) {
        const base = `maps://?q=${encodedName}`;
        if (coordsAvailable) {
            return `${base}&ll=${location.lat},${location.lng}`;
        }
        return base;
    }

    const params = new URLSearchParams();
    params.set("api", "1");

    if (coordsAvailable) {
        params.set("destination", `${location.lat},${location.lng}`);
    }

    if (location.place_id && location.place_id.length > 0) {
        params.set("destination_place_id", location.place_id);
    }

    if (!coordsAvailable) {
        params.set("q", location.name ?? "");
    }

    return `${GOOGLE_MAPS_DIRECTIONS_BASE}?${params.toString()}`;
}

export function buildGoogleSearchUrl(name: string, city?: string | null, fallback = DEFAULT_CITY_FALLBACK): string {
    const trimmedName = name?.trim();
    const resolvedCity = typeof city === "string" && city.trim().length > 0 ? city.trim() : fallback;
    const queryParts = [];
    if (trimmedName) queryParts.push(trimmedName);
    if (resolvedCity) queryParts.push(resolvedCity);

    const query = queryParts.join(" ").trim();
    const params = new URLSearchParams();
    params.set("q", query.length > 0 ? query : trimmedName ?? "");

    return `${GOOGLE_SEARCH_BASE}?${params.toString()}`;
}

export const __internal = {
    isIos,
    isAndroid,
    parseCityFromAddress,
    resolveUserAgent,
    DEFAULT_CITY_FALLBACK,
};


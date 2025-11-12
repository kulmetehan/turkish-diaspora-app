import type { LocationMarker } from "@/api/fetchLocations";
import {
    resolveCityForSearchFallback,
    parseCityFromAddress,
    type LocForCityFallback,
    type ViewportContext as CityViewportContext,
    type KnownCity,
} from "@/lib/cityResolver";
import { KNOWN_CITIES } from "@/config/knownCities";

const GOOGLE_MAPS_DIRECTIONS_BASE = "https://www.google.com/maps/dir/";
const GOOGLE_SEARCH_BASE = "https://www.google.com/search";

type LocForRoute = Pick<LocationMarker, "lat" | "lng" | "place_id"> & {
    name?: string | null;
};

type LocForCity = Pick<LocationMarker, "address" | "city">;

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

function hasCoordinates<T extends { lat: number | null | undefined; lng: number | null | undefined }>(
    location: T
): location is T & { lat: number; lng: number } {
    return typeof location.lat === "number" &&
        Number.isFinite(location.lat) &&
        typeof location.lng === "number" &&
        Number.isFinite(location.lng);
}

export function deriveCityForLocation(location: LocForCity, fallback = ""): string {
    const direct = typeof location.city === "string" && location.city.trim().length > 0
        ? location.city.trim()
        : null;
    const parsed = direct ?? parseCityFromAddress(location.address);
    if (parsed && parsed.trim().length > 0) {
        return parsed.trim();
    }
    return fallback;
}

export function buildRouteUrl(location: LocForRoute, userAgent?: string): string {
    const ua = resolveUserAgent(userAgent);
    const coordsAvailable = hasCoordinates(location);
    const safeName = String(location.name ?? "");
    const encodedName = encodeURIComponent(safeName);

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

    if (typeof location.place_id === "string" && location.place_id.length > 0) {
        params.set("destination_place_id", location.place_id);
    }

    if (!coordsAvailable) {
        params.set("q", safeName);
    }

    return `${GOOGLE_MAPS_DIRECTIONS_BASE}?${params.toString()}`;
}

type BuildGoogleSearchOpts = {
    viewport?: CityViewportContext | null;
    loc?: LocForCityFallback;
    knownCities?: KnownCity[];
};

export function buildGoogleSearchUrl(name: string, city?: string | null, opts?: BuildGoogleSearchOpts): string {
    const trimmedName = typeof name === "string" ? name.trim() : "";
    const knownCities = opts?.knownCities ?? KNOWN_CITIES;

    let cityToUse = typeof city === "string" && city.trim().length > 0 ? city.trim() : null;

    if (!cityToUse) {
        const locForFallback: LocForCityFallback = opts?.loc ?? {
            name,
            city: city ?? null,
        };
        cityToUse = resolveCityForSearchFallback(locForFallback, opts?.viewport ?? null, knownCities);
    }

    const queryParts: string[] = [];
    if (trimmedName) queryParts.push(trimmedName);
    if (cityToUse) queryParts.push(cityToUse);

    const query = queryParts.join(" ").trim();
    const params = new URLSearchParams();
    params.set("q", query.length > 0 ? query : trimmedName);

    return `${GOOGLE_SEARCH_BASE}?${params.toString()}`;
}

export const __internal = {
    isIos,
    isAndroid,
    parseCityFromAddress,
    resolveUserAgent,
};


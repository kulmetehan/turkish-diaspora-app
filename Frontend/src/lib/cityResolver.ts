import type { LocationMarker } from "@/api/fetchLocations";

export interface KnownCity {
    name: string;
    lat: number;
    lng: number;
    bbox?: [number, number, number, number];
}

export interface ViewportContext {
    zoom: number;
    centerLat: number;
    centerLng: number;
    visible?: Array<{ city?: string | null }>;
    selectedCity?: string | null;
}

export interface LocForCityFallback {
    name?: string | null;
    city?: string | null;
    address?: string | null;
    lat?: number | null;
    lng?: number | null;
}

export const MIN_ZOOM_FOR_VIEWPORT = 12;
export const VIEWPORT_VISIBLE_MIN = 10;
export const VIEWPORT_MAJORITY_RATIO = 0.6;
export const NEAR_CITY_MAX_KM = 60;

// Earth radius in kilometers
const EARTH_RADIUS_KM = 6371;

function toRadians(value: number): number {
    return (value * Math.PI) / 180;
}

function isFiniteNumber(value: unknown): value is number {
    return typeof value === "number" && Number.isFinite(value);
}

export function parseCityFromAddress(address?: string | null): string | null {
    if (!address) return null;
    const segments = address
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);

    for (let i = segments.length - 1; i >= 0; i -= 1) {
        let candidate = segments[i];
        candidate = candidate.replace(/\b\d{4}\s?[A-Z]{2}\b/gi, "").trim();
        if (!candidate) continue;

        if (/^(netherlands|nederland|the netherlands)$/i.test(candidate)) {
            continue;
        }

        if (/[a-zA-Z]/.test(candidate)) {
            return candidate;
        }
    }

    return null;
}

function haversineDistanceKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const dLat = toRadians(lat2 - lat1);
    const dLon = toRadians(lng2 - lng1);
    const rLat1 = toRadians(lat1);
    const rLat2 = toRadians(lat2);

    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return EARTH_RADIUS_KM * c;
}

export function nearestKnownCityName(lat: number, lng: number, cities: KnownCity[], maxKm = NEAR_CITY_MAX_KM): string | null {
    if (!isFiniteNumber(lat) || !isFiniteNumber(lng)) return null;
    if (!Array.isArray(cities) || cities.length === 0) return null;

    let best: { name: string; distance: number } | null = null;

    for (const city of cities) {
        if (!isFiniteNumber(city.lat) || !isFiniteNumber(city.lng)) continue;
        const distance = haversineDistanceKm(lat, lng, city.lat, city.lng);
        if (distance > maxKm) continue;

        if (!best || distance < best.distance) {
            best = { name: city.name, distance };
        }
    }

    return best?.name ?? null;
}

export function majorityCityFromVisible(
    visible?: Array<{ city?: string | null }>,
    min = VIEWPORT_VISIBLE_MIN,
    ratio = VIEWPORT_MAJORITY_RATIO
): string | null {
    if (!Array.isArray(visible) || visible.length < min) return null;

    const counts = new Map<string, number>();
    let total = 0;

    for (const entry of visible) {
        const city = typeof entry?.city === "string" ? entry.city.trim() : "";
        if (!city) continue;
        total += 1;
        counts.set(city, (counts.get(city) ?? 0) + 1);
    }

    if (total < min || counts.size === 0) {
        return null;
    }

    let bestCity: string | null = null;
    let bestCount = 0;

    counts.forEach((count, city) => {
        if (count > bestCount) {
            bestCount = count;
            bestCity = city;
        }
    });

    if (bestCity && bestCount / total >= ratio) {
        return bestCity;
    }

    return null;
}

export function resolveCityForSearchFallback(
    loc: LocForCityFallback,
    viewport: ViewportContext | null,
    knownCities: KnownCity[]
): string | null {
    const directCity = typeof loc?.city === "string" ? loc.city.trim() : "";
    if (directCity) {
        return directCity;
    }

    const parsedCity = parseCityFromAddress(loc?.address);
    if (parsedCity) {
        return parsedCity;
    }

    if (isFiniteNumber(loc?.lat) && isFiniteNumber(loc?.lng)) {
        const nearestByLoc = nearestKnownCityName(loc.lat!, loc.lng!, knownCities);
        if (nearestByLoc) {
            return nearestByLoc;
        }
    }

    const zoom = isFiniteNumber(viewport?.zoom) ? viewport!.zoom : null;
    const meetsViewportZoom = zoom !== null && zoom >= MIN_ZOOM_FOR_VIEWPORT;

    const selectedCity =
        meetsViewportZoom && typeof viewport?.selectedCity === "string"
            ? viewport.selectedCity.trim()
            : "";
    if (selectedCity) {
        return selectedCity;
    }

    if (meetsViewportZoom) {
        const majority = majorityCityFromVisible(viewport?.visible);
        if (majority) {
            return majority;
        }
    }

    if (isFiniteNumber(viewport?.centerLat) && isFiniteNumber(viewport?.centerLng)) {
        const nearestByViewport = nearestKnownCityName(
            viewport!.centerLat,
            viewport!.centerLng,
            knownCities
        );
        if (nearestByViewport) {
            return nearestByViewport;
        }
    }

    return null;
}

// Convenience helper when working with full LocationMarker objects
export function toLocForCityFallback(location: LocationMarker): LocForCityFallback {
    return {
        name: location.name,
        city: location.city,
        address: location.address,
        lat: location.lat,
        lng: location.lng,
    };
}


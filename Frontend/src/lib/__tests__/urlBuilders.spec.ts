import { describe, expect, it } from "vitest";

import type { LocationMarker } from "@/api/fetchLocations";
import { buildGoogleSearchUrl, buildRouteUrl, deriveCityForLocation, __internal } from "@/lib/urlBuilders";
import { KNOWN_CITIES } from "@/config/knownCities";

const baseLocation: LocationMarker = {
    id: "1",
    name: "Anadolu Restaurant",
    lat: 51.9225,
    lng: 4.47917,
    category: "restaurant",
    state: "VERIFIED",
    rating: null,
    confidence_score: 0.93,
    is_turkish: true,
};

describe("deriveCityForLocation", () => {
    it("prefers explicit city field when provided", () => {
        const city = deriveCityForLocation({ ...baseLocation, city: "Rotterdam", address: null });
        expect(city).toBe("Rotterdam");
    });

    it("extracts city from address when possible", () => {
        const city = deriveCityForLocation({
            ...baseLocation,
            address: "Westblaak 123, 3012 AK Rotterdam, Netherlands",
            city: undefined,
        });
        expect(city).toBe("Rotterdam");
    });

    it("falls back to default when address is unavailable", () => {
        const city = deriveCityForLocation({ ...baseLocation, address: null, city: undefined }, "Fallback City");
        expect(city).toBe("Fallback City");
    });
});

describe("buildRouteUrl", () => {
    it("returns Apple Maps URL on iOS", () => {
        const url = buildRouteUrl(baseLocation, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)");
        expect(url).toContain("maps://?q=Anadolu%20Restaurant");
        expect(url).toContain("&ll=51.9225,4.47917");
    });

    it("returns Google Maps direction URL with coordinates and place id", () => {
        const url = buildRouteUrl({ ...baseLocation, place_id: "ChIJ123456789" }, "Mozilla/5.0 (Linux; Android 14)");
        expect(url).toContain("https://www.google.com/maps/dir/?");
        expect(url).toContain("api=1");
        expect(url).toContain("destination=51.9225%2C4.47917");
        expect(url).toContain("destination_place_id=ChIJ123456789");
    });

    it("falls back to query when coordinates missing", () => {
        const url = buildRouteUrl({ ...baseLocation, lat: null, lng: null }, "Mozilla/5.0 (Linux; Android 14)");
        const parsed = new URL(url);
        expect(parsed.searchParams.get("q")).toBe("Anadolu Restaurant");
        expect(parsed.searchParams.has("destination")).toBe(false);
    });
});

describe("buildGoogleSearchUrl", () => {
    it("includes name and provided city in query", () => {
        const url = buildGoogleSearchUrl(baseLocation.name, "Rotterdam");
        const parsed = new URL(url);
        expect(parsed.origin + parsed.pathname).toBe("https://www.google.com/search");
        expect(parsed.searchParams.get("q")).toBe("Anadolu Restaurant Rotterdam");
    });

    it("resolves nearest city when location missing city", () => {
        const url = buildGoogleSearchUrl(baseLocation.name, undefined, {
            loc: { ...baseLocation, city: null },
            viewport: null,
            knownCities: KNOWN_CITIES,
        });
        const parsed = new URL(url);
        expect(parsed.searchParams.get("q")).toBe("Anadolu Restaurant Rotterdam");
    });
});

describe("__internal helpers", () => {
    it("detects iOS user agents", () => {
        expect(__internal.isIos("Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X)")).toBe(true);
        expect(__internal.isIos("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")).toBe(false);
    });

    it("detects Android user agents", () => {
        expect(__internal.isAndroid("Mozilla/5.0 (Linux; Android 14; Pixel 7)")).toBe(true);
        expect(__internal.isAndroid("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)")).toBe(false);
    });
});


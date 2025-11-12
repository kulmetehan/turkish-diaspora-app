import { describe, expect, it } from "vitest";

import {
    MIN_ZOOM_FOR_VIEWPORT,
    resolveCityForSearchFallback,
    majorityCityFromVisible,
    nearestKnownCityName,
    parseCityFromAddress,
} from "@/lib/cityResolver";
import { KNOWN_CITIES } from "@/config/knownCities";
import { buildGoogleSearchUrl } from "@/lib/urlBuilders";

const SAMPLE_KNOWN_CITIES = [
    ...KNOWN_CITIES,
    { name: "Amsterdam", lat: 52.3676, lng: 4.9041 },
    { name: "Utrecht", lat: 52.0907, lng: 5.1214 },
];

describe("cityResolver helpers", () => {
    it("returns nearest known city based on coordinates", () => {
        const city = resolveCityForSearchFallback(
            { city: null, address: null, lat: 52.0702, lng: 4.3136 },
            null,
            SAMPLE_KNOWN_CITIES
        );
        expect(city).toBe("Den Haag");
    });

    it("prefers selected city when zoom is sufficient", () => {
        const city = resolveCityForSearchFallback(
            { city: null, address: null, lat: null, lng: null },
            {
                zoom: MIN_ZOOM_FOR_VIEWPORT,
                centerLat: 52.3676,
                centerLng: 4.9041,
                selectedCity: "Amsterdam",
                visible: undefined,
            },
            SAMPLE_KNOWN_CITIES
        );
        expect(city).toBe("Amsterdam");
    });

    it("derives majority city from visible samples", () => {
        const majority = resolveCityForSearchFallback(
            { city: null, address: null },
            {
                zoom: MIN_ZOOM_FOR_VIEWPORT + 1,
                centerLat: 51.92,
                centerLng: 4.48,
                selectedCity: null,
                visible: [
                    ...Array.from({ length: 7 }, () => ({ city: "Rotterdam" })),
                    ...Array.from({ length: 3 }, () => ({ city: "Schiedam" })),
                    { city: "Rotterdam" },
                    { city: "Rotterdam" },
                ],
            },
            SAMPLE_KNOWN_CITIES
        );
        expect(majority).toBe("Rotterdam");
    });

    it("falls back to viewport center nearest city when zoom low", () => {
        const city = resolveCityForSearchFallback(
            { city: null, address: null },
            {
                zoom: MIN_ZOOM_FOR_VIEWPORT - 1,
                centerLat: 52.0116,
                centerLng: 4.3571,
                selectedCity: "Amsterdam",
                visible: [
                    ...Array.from({ length: 6 }, () => ({ city: "Amsterdam" })),
                    ...Array.from({ length: 4 }, () => ({ city: "Rotterdam" })),
                ],
            },
            SAMPLE_KNOWN_CITIES
        );
        expect(city).toBe("Delft");
    });

    it("computes majority only when visible sample sufficient", () => {
        const result = majorityCityFromVisible(
            [{ city: "Rotterdam" }, { city: "Rotterdam" }, { city: "Den Haag" }],
            5,
            0.6
        );
        expect(result).toBeNull();
    });

    it("parses city names from address strings", () => {
        expect(parseCityFromAddress("Kruiskade 21, 3012 EE Rotterdam, Netherlands")).toBe("Rotterdam");
        expect(parseCityFromAddress("Damrak 1, 1012LG Amsterdam, Nederland")).toBe("Amsterdam");
        expect(parseCityFromAddress(null)).toBeNull();
    });

    it("returns null when no known city is near enough", () => {
        const city = nearestKnownCityName(48.8566, 2.3522, SAMPLE_KNOWN_CITIES, 30);
        expect(city).toBeNull();
    });
});

describe("buildGoogleSearchUrl integration", () => {
    it("encodes names with punctuation and diacritics without extra spaces", () => {
        const url = buildGoogleSearchUrl("O'Leary’s Café 😊", null, {
            loc: { city: null, address: null, lat: 51.9244, lng: 4.4777 },
            viewport: null,
            knownCities: SAMPLE_KNOWN_CITIES,
        });
        const parsed = new URL(url);
        expect(parsed.searchParams.get("q")).toBe("O'Leary’s Café 😊 Rotterdam");
    });

    it("respects provided city even when viewport context exists", () => {
        const url = buildGoogleSearchUrl("Test Location", "Custom City", {
            loc: { city: "Custom City", address: null, lat: null, lng: null },
            viewport: {
                zoom: MIN_ZOOM_FOR_VIEWPORT + 2,
                centerLat: 51.9244,
                centerLng: 4.4777,
                selectedCity: "Rotterdam",
                visible: Array.from({ length: 12 }, () => ({ city: "Rotterdam" })),
            },
            knownCities: SAMPLE_KNOWN_CITIES,
        });
        const parsed = new URL(url);
        expect(parsed.searchParams.get("q")).toBe("Test Location Custom City");
    });
});


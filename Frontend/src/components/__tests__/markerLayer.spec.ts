import { ensureBaseLayers, buildMarkerGeoJSON, MarkerLayerIds } from "@/components/markerLayerUtils";
import type { LocationMarker } from "@/api/fetchLocations";
import { describe, expect, it } from "vitest";

type LayerConfig = { id: string };

class MapStub {
    addLayerCount = 0;
    addSourceCount = 0;
    layers = new Map<string, LayerConfig>();
    sources = new Map<string, unknown>();

    getSource(id: string) {
        return this.sources.get(id) ?? null;
    }

    addSource(id: string, config: unknown) {
        this.addSourceCount += 1;
        this.sources.set(id, config);
    }

    getLayer(id: string) {
        return this.layers.get(id) ?? null;
    }

    addLayer(layer: LayerConfig) {
        this.addLayerCount += 1;
        this.layers.set(layer.id, layer);
    }

    // Unused Mapbox APIs for this test scenario
    on() {}
    once(_event: string, handler: (...args: any[]) => void) { handler(); }
    off() {}
    getStyle() { return { sources: {} }; }
}

const baseLocations: LocationMarker[] = [
    {
        id: "101",
        name: "Test Location",
        lat: 51.92,
        lng: 4.47,
        category: "restaurant",
        state: "VERIFIED",
        rating: null,
        confidence_score: 0.95,
        is_turkish: true,
    },
    {
        id: "202",
        name: "Another",
        lat: 51.93,
        lng: 4.48,
        category: "bakery",
        state: "VERIFIED",
        rating: null,
        confidence_score: 0.91,
        is_turkish: true,
    },
];

describe("marker layer utilities", () => {
    it("builds GeoJSON features with stable ids", () => {
        const first = buildMarkerGeoJSON(baseLocations);
        expect(first.features.map((f) => f.properties.id)).toEqual(["101", "202"]);

        const reversed = buildMarkerGeoJSON([...baseLocations].reverse());
        expect(reversed.features.map((f) => f.properties.id)).toEqual(["202", "101"]);
    });

    it("does not re-add sources or layers on repeated ensureBaseLayers calls", () => {
        const map = new MapStub();

        ensureBaseLayers(map as unknown as any);

        const { SRC_ID, L_CLUSTER, L_CLUSTER_COUNT, L_POINT, L_HI } = MarkerLayerIds;

        expect(map.getSource(SRC_ID)).toBeTruthy();
        expect(map.getLayer(L_CLUSTER)).toBeTruthy();
        expect(map.getLayer(L_CLUSTER_COUNT)).toBeTruthy();
        expect(map.getLayer(L_POINT)).toBeTruthy();
        expect(map.getLayer(L_HI)).toBeTruthy();

        const sourceCount = map.addSourceCount;
        const layerCount = map.addLayerCount;

        ensureBaseLayers(map as unknown as any);

        expect(map.addSourceCount).toBe(sourceCount);
        expect(map.addLayerCount).toBe(layerCount);
    });
});


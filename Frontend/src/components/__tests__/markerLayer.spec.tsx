import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

import { ensureBaseLayers, buildMarkerGeoJSON, MarkerLayerIds } from "@/components/markerLayerUtils";
import MarkerLayer from "@/components/MarkerLayer";
import type { LocationMarker } from "@/api/fetchLocations";
import { describe, expect, it, vi } from "vitest";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

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

        const sourceConfig = map.getSource(SRC_ID) as any;
        expect(sourceConfig).toBeTruthy();
        expect(sourceConfig.promoteId).toBe("id");

        const pointLayer = map.getLayer(L_POINT) as any;
        expect(pointLayer).toBeTruthy();
        expect(pointLayer.paint["circle-color"]).toEqual([
            "case",
            ["boolean", ["feature-state", "selected"], false],
            "#22c55e",
            "#e11d48",
        ]);
        expect(pointLayer.paint["circle-stroke-color"]).toEqual([
            "case",
            ["boolean", ["feature-state", "selected"], false],
            "#14532d",
            "#fff",
        ]);

        expect(map.getLayer(L_CLUSTER)).toBeTruthy();
        expect(map.getLayer(L_CLUSTER_COUNT)).toBeTruthy();
        expect(map.getLayer(L_HI)).toBeTruthy();

        const sourceCount = map.addSourceCount;
        const layerCount = map.addLayerCount;

        ensureBaseLayers(map as unknown as any);

        expect(map.addSourceCount).toBe(sourceCount);
        expect(map.addLayerCount).toBe(layerCount);
    });
});

describe("MarkerLayer feature-state integration", () => {
    class InteractiveMapStub {
        handlers = new Map<string, Set<Function>>();
        layers = new Map<string, any>();
        sources = new Map<string, any>();
        setFilter = vi.fn();
        setFeatureState = vi.fn();
        removeFeatureState = vi.fn();

        getStyle() {
            return { sources: this.sources };
        }
        addSource(id: string, config: any) {
            const source = {
                ...config,
                setData: vi.fn(),
                getClusterExpansionZoom: vi.fn(),
            };
            this.sources.set(id, source);
        }
        getSource(id: string) {
            return this.sources.get(id) ?? null;
        }
        addLayer(layer: any) {
            this.layers.set(layer.id, layer);
        }
        getLayer(id: string) {
            return this.layers.get(id) ?? null;
        }
        on(event: string, handler: Function) {
            const set = this.handlers.get(event) ?? new Set();
            set.add(handler);
            this.handlers.set(event, set);
        }
        off(event: string, handler: Function) {
            const set = this.handlers.get(event);
            if (!set) return;
            set.delete(handler);
        }
        once(event: string, handler: Function) {
            handler();
        }
        trigger(event: string) {
            const set = this.handlers.get(event);
            if (!set) return;
            set.forEach((handler) => handler());
        }
        queryRenderedFeatures() {
            return [];
        }
    }

    it("sets and clears feature-state when selection changes", async () => {
        const map = new InteractiveMapStub();
        const container = document.createElement("div");
        document.body.appendChild(container);
        const root = createRoot(container);

        await act(async () => {
            root.render(
                <MarkerLayer
                    map={map as unknown as any}
                    locations={baseLocations}
                    selectedId={null}
                />,
            );
            await Promise.resolve();
        });

        expect(map.setFeatureState).not.toHaveBeenCalled();

        await act(async () => {
            root.render(
                <MarkerLayer
                    map={map as unknown as any}
                    locations={baseLocations}
                    selectedId="101"
                />,
            );
            await Promise.resolve();
        });

        expect(map.setFeatureState).toHaveBeenCalledWith(
            { source: MarkerLayerIds.SRC_ID, id: "101" },
            { selected: true },
        );

        map.setFeatureState.mockClear();

        await act(async () => {
            root.render(
                <MarkerLayer
                    map={map as unknown as any}
                    locations={baseLocations}
                    selectedId="202"
                />,
            );
            await Promise.resolve();
        });

        expect(map.removeFeatureState).toHaveBeenCalledWith({ source: MarkerLayerIds.SRC_ID, id: "101" }, "selected");
        expect(map.setFeatureState).toHaveBeenCalledWith(
            { source: MarkerLayerIds.SRC_ID, id: "202" },
            { selected: true },
        );

        map.removeFeatureState.mockClear();
        map.setFeatureState.mockClear();

        await act(async () => {
            root.render(
                <MarkerLayer
                    map={map as unknown as any}
                    locations={baseLocations}
                    selectedId={null}
                />,
            );
            await Promise.resolve();
        });

        expect(map.removeFeatureState).toHaveBeenCalledWith({ source: MarkerLayerIds.SRC_ID, id: "202" }, "selected");

        // Trigger style reload to ensure selected state reapplies
        map.setFeatureState.mockClear();
        await act(async () => {
            root.render(
                <MarkerLayer
                    map={map as unknown as any}
                    locations={baseLocations}
                    selectedId="101"
                />,
            );
            await Promise.resolve();
        });
        map.setFeatureState.mockClear();
        map.trigger("styledata");
        expect(map.setFeatureState).toHaveBeenCalledWith(
            { source: MarkerLayerIds.SRC_ID, id: "101" },
            { selected: true },
        );

        await act(async () => {
            root.unmount();
        });
        container.remove();
    });
});


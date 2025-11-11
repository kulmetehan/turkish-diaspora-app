import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";

import { ensureBaseLayers, buildMarkerGeoJSON, MarkerLayerIds } from "@/components/markerLayerUtils";
import MarkerLayer from "@/components/MarkerLayer";
import type { LocationMarker } from "@/api/fetchLocations";
import { CATEGORY_ICON_IDS, DEFAULT_ICON_ID, ICON_BASE_ID, ensureCategoryIcons } from "@/lib/map/categoryIcons";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

type LayerConfig = { id: string };

const originalCreateElement = document.createElement.bind(document);
const originalImage = (globalThis as any).Image;
let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
    vi.stubGlobal(
        "createImageBitmap",
        vi.fn(async () => ({ close: vi.fn() }) as unknown as ImageBitmap),
    );

    class FakeImage {
        decoding = "sync";
        onload: (() => void) | null = null;
        onerror: ((err?: unknown) => void) | null = null;
        #src = "";

        get src() {
            return this.#src;
        }

        set src(value: string) {
            this.#src = value;
            queueMicrotask(() => {
                this.onload?.();
            });
        }

        async decode(): Promise<void> {
            return Promise.resolve();
        }
    }

    vi.stubGlobal("Image", FakeImage as unknown as typeof Image);

    vi.spyOn(document, "createElement").mockImplementation((tagName: string, ...rest: any[]) => {
        if (tagName.toLowerCase() === "canvas") {
            const mockCtx = {
                scale: vi.fn(),
                clearRect: vi.fn(),
                drawImage: vi.fn(),
                save: vi.fn(),
                restore: vi.fn(),
                beginPath: vi.fn(),
                ellipse: vi.fn(),
                arc: vi.fn(),
                moveTo: vi.fn(),
                lineTo: vi.fn(),
                stroke: vi.fn(),
                fill: vi.fn(),
                quadraticCurveTo: vi.fn(),
                createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
                setTransform: vi.fn(),
                fillStyle: "",
                strokeStyle: "",
                lineWidth: 0,
            };
            return {
                width: 0,
                height: 0,
                getContext: vi.fn(() => mockCtx),
            } as unknown as HTMLCanvasElement;
        }

        return originalCreateElement(tagName, ...rest);
    });

    createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockImplementation(() => "blob:mock");
    revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
});

afterEach(() => {
    vi.unstubAllGlobals();
    if (originalImage) {
        (globalThis as any).Image = originalImage;
    } else {
        delete (globalThis as any).Image;
    }
    createObjectURLSpy.mockRestore();
    revokeObjectURLSpy.mockRestore();
    vi.restoreAllMocks();
});

class MapStub {
    addLayerCount = 0;
    addSourceCount = 0;
    layers = new Map<string, LayerConfig>();
    sources = new Map<string, unknown>();
    images = new Map<string, { image: unknown; options: unknown }>();
    styleKey = "test-style";

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

    addLayer(layer: LayerConfig, beforeId?: string) {
        this.addLayerCount += 1;
        this.layers.set(layer.id, layer);
        if (beforeId && this.layers.has(beforeId)) {
            this.moveLayer(layer.id, beforeId);
        }
    }

    addImage(id: string, image: unknown, options: unknown) {
        this.images.set(id, { image, options });
    }

    hasImage(id: string) {
        return this.images.has(id);
    }

    listImages() {
        return Array.from(this.images.keys());
    }

    listImages() {
        return Array.from(this.images.keys());
    }

    triggerRepaint() {}
    setLayoutProperty() {}
    getStyle() {
        return { sprite: this.styleKey, name: this.styleKey, sources: {} };
    }

    moveLayer(id: string, beforeId?: string) {
        if (!this.layers.has(id)) return;
        const layer = this.layers.get(id)!;
        this.layers.delete(id);
        const entries = Array.from(this.layers.entries());
        this.layers.clear();
        if (beforeId) {
            let inserted = false;
            for (const [key, value] of entries) {
                if (key === beforeId && !inserted) {
                    this.layers.set(id, layer);
                    inserted = true;
                }
                this.layers.set(key, value);
            }
            if (!inserted) {
                this.layers.set(id, layer);
            }
        } else {
            for (const [key, value] of entries) {
                this.layers.set(key, value);
            }
            this.layers.set(id, layer);
        }
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
        expect(first.features.map((f) => f.properties.icon)).toEqual([
            `${ICON_BASE_ID}-restaurant`,
            `${ICON_BASE_ID}-bakery`,
        ]);

        const reversed = buildMarkerGeoJSON([...baseLocations].reverse());
        expect(reversed.features.map((f) => f.properties.id)).toEqual(["202", "101"]);
        expect(reversed.features.map((f) => f.properties.categoryKey)).toEqual(["bakery", "restaurant"]);
    });

    it("does not re-add sources or layers on repeated ensureBaseLayers calls", () => {
        const map = new MapStub();

        ensureBaseLayers(map as unknown as any);

        const { SRC_ID, L_CLUSTER, L_CLUSTER_COUNT, L_HALO, L_POINT } = MarkerLayerIds;

        const sourceConfig = map.getSource(SRC_ID) as any;
        expect(sourceConfig).toBeTruthy();
        expect(sourceConfig.promoteId).toBe("id");

        const haloLayer = map.getLayer(L_HALO) as any;
        expect(haloLayer).toBeTruthy();
        expect(haloLayer.type).toBe("circle");
        expect(haloLayer.paint["circle-radius"]).toBeDefined();

        const pointLayer = map.getLayer(L_POINT) as any;
        expect(pointLayer).toBeTruthy();
        expect(pointLayer.type).toBe("symbol");
        expect(pointLayer.layout["icon-image"]).toEqual([
            "coalesce",
            ["image", ["get", "icon"]],
            ["image", DEFAULT_ICON_ID],
        ]);
        expect(pointLayer.layout["icon-size"]).toEqual(1);
        expect(pointLayer.paint["icon-opacity"]).toEqual([
            "case",
            ["boolean", ["feature-state", "selected"], false],
            1,
            0.82,
        ]);

        expect(map.getLayer(L_CLUSTER)).toBeTruthy();
        expect(map.getLayer(L_CLUSTER_COUNT)).toBeTruthy();

        const sourceCount = map.addSourceCount;
        const layerCount = map.addLayerCount;

        ensureBaseLayers(map as unknown as any);

        expect(map.addSourceCount).toBe(sourceCount);
        expect(map.addLayerCount).toBe(layerCount);
    });

    it("registers every category icon id", async () => {
        const map = new MapStub();
        await ensureCategoryIcons(map as unknown as any, 2);
        const registered = map.listImages();
        for (const id of CATEGORY_ICON_IDS) {
            expect(registered).toContain(id);
        }
        expect(registered).toContain(DEFAULT_ICON_ID);
    });
});

describe("MarkerLayer feature-state integration", () => {
    class InteractiveMapStub {
        handlers = new Map<string, Set<Function>>();
        layers = new Map<string, any>();
        sources = new Map<string, any>();
        images = new Map<string, any>();
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
        addImage(id: string, image: unknown) {
            this.images.set(id, image);
        }
        hasImage(id: string) {
            return this.images.has(id);
        }
        listImages() {
            return Array.from(this.images.keys());
        }
        moveLayer() {}
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


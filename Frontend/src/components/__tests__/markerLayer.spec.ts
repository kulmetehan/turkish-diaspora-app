import { ensureSourceAndLayersOnce } from "@/components/MarkerLayer";
import type { Map as MapboxMap } from "mapbox-gl";
import { describe, expect, it } from "vitest";

type LayerConfig = {
    id: string;
};

class StubMap {
    styleLoaded = false;
    sources = new Map<string, unknown>();
    layers = new Map<string, LayerConfig>();
    addSourceCount = 0;
    addLayerCount = 0;
    moveLayerCount = 0;

    isStyleLoaded() {
        return this.styleLoaded;
    }

    setStyleLoaded(value: boolean) {
        this.styleLoaded = value;
    }

    getSource(id: string) {
        return this.sources.get(id);
    }

    addSource(id: string, config: unknown) {
        this.sources.set(id, config);
        this.addSourceCount += 1;
    }

    getLayer(id: string) {
        return this.layers.get(id);
    }

    addLayer(config: LayerConfig) {
        this.layers.set(config.id, config);
        this.addLayerCount += 1;
    }

    moveLayer() {
        this.moveLayerCount += 1;
    }

    resetStyle() {
        this.sources.clear();
        this.layers.clear();
    }
}

describe("ensureSourceAndLayersOnce", () => {
    it("waits for style readiness before attaching", () => {
        const map = new StubMap();
        const attachedRef = { current: null };

        const resultWhenNotReady = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: false,
            styleVersion: 1,
            attachedStyleVersionRef: attachedRef,
        });

        expect(resultWhenNotReady).toBe(false);
        expect(map.addSourceCount).toBe(0);

        const resultWhenStyleLoading = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: true,
            styleVersion: 1,
            attachedStyleVersionRef: attachedRef,
        });

        expect(resultWhenStyleLoading).toBe(false);
        expect(map.addSourceCount).toBe(0);

        map.setStyleLoaded(true);

        const resultLoaded = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: true,
            styleVersion: 1,
            attachedStyleVersionRef: attachedRef,
        });

        expect(resultLoaded).toBe(true);
        expect(attachedRef.current).toBe(1);
        expect(map.addSourceCount).toBe(1);
    });

    it("runs only once per styleVersion and reattaches after reset", () => {
        const map = new StubMap();
        map.setStyleLoaded(true);
        const attachedRef: { current: number | null } = { current: null };

        const firstAttach = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: true,
            styleVersion: 4,
            attachedStyleVersionRef: attachedRef,
        });

        expect(firstAttach).toBe(true);
        expect(map.addSourceCount).toBe(1);

        const repeatSameVersion = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: true,
            styleVersion: 4,
            attachedStyleVersionRef: attachedRef,
        });

        expect(repeatSameVersion).toBe(true);
        expect(map.addSourceCount).toBe(1);

        map.resetStyle();

        const nextVersionAttach = ensureSourceAndLayersOnce({
            map: map as unknown as MapboxMap,
            styleReady: true,
            styleVersion: 5,
            attachedStyleVersionRef: attachedRef,
        });

        expect(nextVersionAttach).toBe(true);
        expect(attachedRef.current).toBe(5);
        expect(map.addSourceCount).toBe(2);
    });
});


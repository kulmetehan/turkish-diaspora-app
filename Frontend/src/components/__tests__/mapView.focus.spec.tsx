import React from "react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createRoot, type Root } from "react-dom/client";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
if (!("requestAnimationFrame" in globalThis)) {
  (globalThis as any).requestAnimationFrame = (callback: FrameRequestCallback) => {
    callback(performance.now());
    return 0;
  };
  (globalThis as any).cancelAnimationFrame = () => {};
}

const markerLayerCapture = vi.hoisted(() => ({ current: null as any }));

vi.mock("@/components/MarkerLayer", () => ({
  __esModule: true,
  default: (props: any) => {
    markerLayerCapture.current = props;
    return null;
  },
}));

const mapboxMocks = vi.hoisted(() => {
  const easeToSpy = vi.fn();
  const setCenterSpy = vi.fn();
  const setZoomSpy = vi.fn();
  const setFeatureStateSpy = vi.fn();
  const removeFeatureStateSpy = vi.fn();

  class MapMock {
    static instances: MapMock[] = [];
    static autoLoadDefault = true;
    static styleLoadedDefault = true;
    handlers: Record<string, Array<{ fn: Function; layer?: string; label?: string }>> = {};
    private moving = false;
    zoom = 12;
    bearing = 0;
    pitch = 0;
    autoLoad = true;
    styleLoaded = true;
    sources = new Map<string, any>();
    layers = new Map<string, any>();

    constructor() {
      MapMock.instances.push(this);
      this.autoLoad = MapMock.autoLoadDefault;
      this.styleLoaded = MapMock.styleLoadedDefault;
    }
    addControl() {}
    getStyle() {
      return { sources: Object.fromEntries(this.sources) };
    }
    getSource(id: string) {
      return this.sources.get(id) ?? null;
    }
    addSource(id: string, config: any) {
      this.sources.set(id, config);
    }
    getLayer(id: string) {
      return this.layers.get(id) ?? null;
    }
    addLayer(layer: any) {
      if (layer?.id) {
        this.layers.set(layer.id, layer);
      }
    }
    setFilter() {}
    remove() {
      this.handlers = {};
      this.moving = false;
    }
    on(event: string, layerOrHandler: any, maybeHandler?: (...args: any[]) => void) {
      let layer: string | undefined;
      let handler: (...args: any[]) => void;
      if (typeof layerOrHandler === "function" || typeof maybeHandler !== "function") {
        handler = layerOrHandler;
      } else {
        layer = String(layerOrHandler);
        handler = maybeHandler;
      }
      this.handlers[event] = this.handlers[event] ?? [];
      this.handlers[event].push({ fn: handler, layer, label: handler?.name });
      if (event === "load" && this.autoLoad) {
        Promise.resolve().then(() => handler());
      }
    }
    off(event: string, handler: (...args: any[]) => void) {
      const list = this.handlers[event];
      if (!list) return;
      this.handlers[event] = list.filter((entry) => entry.fn !== handler);
    }
    once(event: string, layerOrHandler: any, maybeHandler?: (...args: any[]) => void) {
      let layer: string | undefined;
      let handler: (...args: any[]) => void;
      if (typeof layerOrHandler === "function" || typeof maybeHandler !== "function") {
        handler = layerOrHandler;
      } else {
        layer = String(layerOrHandler);
        handler = maybeHandler;
      }
      const wrapped = (...args: any[]) => {
        handler(...args);
        this.off(event, wrapped);
      };
      if (layer) {
        this.on(event, layer, wrapped);
      } else {
        this.on(event, wrapped);
      }
    }
    isStyleLoaded() {
      return this.styleLoaded;
    }
    loaded() {
      return this.styleLoaded;
    }
    easeTo(options: any) {
      this.moving = true;
      if (typeof options.zoom === "number") {
        this.zoom = options.zoom;
      }
      if (typeof options.bearing === "number") {
        this.bearing = options.bearing;
      }
      if (typeof options.pitch === "number") {
        this.pitch = options.pitch;
      }
      easeToSpy(options);
      Promise.resolve().then(() => {
        this.handlers["move"]?.forEach((entry) => entry.fn());
        this.moving = false;
        this.handlers["moveend"]?.forEach((entry) => entry.fn());
        this.handlers["idle"]?.forEach((entry) => entry.fn());
      });
    }
    setCenter(center: any) {
      setCenterSpy(center);
    }
    setZoom(zoom: number) {
      setZoomSpy(zoom);
    }
    getZoom() {
      return this.zoom;
    }
    isMoving() {
      return this.moving;
    }
    getBounds() {
      return {
        getSouthWest: () => ({ lng: 4.47, lat: 51.92 }),
        getNorthEast: () => ({ lng: 4.48, lat: 51.93 }),
      };
    }
    project() {
      return { x: 400, y: 300 };
    }
    getCanvas() {
      return { clientWidth: 800, clientHeight: 600 };
    }
    queryRenderedFeatures() {
      return [];
    }
    stop() {
      this.moving = false;
    }
    setFeatureState(params: any, state: any) {
      setFeatureStateSpy(params, state);
    }
    removeFeatureState(params: any) {
      removeFeatureStateSpy(params);
    }
    trigger(event: string, arg?: any, layerEvent?: any) {
      if (event === "load") {
        this.styleLoaded = true;
      }
      if (typeof arg === "string") {
        const layer = arg;
        this.handlers[event]?.forEach((entry) => {
          if (entry.layer === layer) {
            entry.fn(layerEvent);
          }
        });
        return;
      }
      this.handlers[event]?.forEach((entry) => {
        if (!entry.layer) {
          entry.fn(arg);
        }
      });
    }
  }

  class PopupMock {
    static instances: PopupMock[] = [];
    options: any;
    offset: any;
    element: HTMLElement;
    added = false;
    lngLat: any = null;
    handlers: Record<string, Function[]> = {};

    constructor(options?: any) {
      this.options = options ?? {};
      this.offset = this.options?.offset ?? null;
      this.element = document.createElement("div");
      this.element.className = "tda-preview-popup";
      const content = document.createElement("div");
      content.className = "mapboxgl-popup-content";
      const card = document.createElement("div");
      card.className = "tda-card";
      card.style.width = "260px";
      card.style.height = "120px";
      content.appendChild(card);
      this.element.appendChild(content);
      PopupMock.instances.push(this);
    }

    setLngLat(value: any) { this.lngLat = value; return this; }
    setMaxWidth() { return this; }
    setDOMContent(dom: HTMLElement) {
      this.element.querySelector(".mapboxgl-popup-content")?.appendChild(dom);
      return this;
    }
    addTo() { this.added = true; return this; }
    setOffset(value: any) { this.offset = value; return this; }
    getElement() {
      return this.element;
    }
    on(event: string, handler: (...args: any[]) => void) {
      this.handlers[event] = this.handlers[event] ?? [];
      this.handlers[event].push(handler);
      return this;
    }
    remove() {
      this.added = false;
    }
    close() {
      this.handlers["close"]?.forEach((handler) => handler());
    }
  }

  class NavigationControlMock {}

  return { easeToSpy, setCenterSpy, setZoomSpy, setFeatureStateSpy, removeFeatureStateSpy, MapMock, PopupMock, NavigationControlMock };
});

vi.mock("mapbox-gl", () => {
  const { MapMock, PopupMock, NavigationControlMock } = mapboxMocks;
  return {
    __esModule: true,
    default: { accessToken: "", Map: MapMock, Popup: PopupMock, NavigationControl: NavigationControlMock },
    Map: MapMock,
    Popup: PopupMock,
    NavigationControl: NavigationControlMock,
  };
});

const {
  easeToSpy,
  setCenterSpy,
  setZoomSpy,
  setFeatureStateSpy,
  removeFeatureStateSpy,
  MapMock,
  PopupMock,
} = mapboxMocks;

import MapView from "@/components/MapView";
import type { LocationMarker } from "@/api/fetchLocations";
import { MARKER_POINT_OUTER_RADIUS } from "@/components/markerLayerUtils";

const SAMPLE: LocationMarker[] = [
  {
    id: "1",
    name: "Focus Spot",
    lat: 51.924,
    lng: 4.475,
    category: "restaurant",
    state: "VERIFIED",
    rating: null,
    confidence_score: 0.9,
    is_turkish: true,
  },
  {
    id: "2",
    name: "Second Spot",
    lat: 51.925,
    lng: 4.478,
    category: "bakery",
    state: "VERIFIED",
    rating: null,
    confidence_score: 0.85,
    is_turkish: false,
  },
];

let container: HTMLDivElement;
let root: Root;
const highlightSpy = vi.fn();
const openDetailSpy = vi.fn();
const focusConsumedSpy = vi.fn();

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  mapboxMocks.PopupMock.instances = [];
  mapboxMocks.MapMock.instances = [];
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  easeToSpy.mockClear();
  setCenterSpy.mockClear();
  setZoomSpy.mockClear();
  highlightSpy.mockClear();
  openDetailSpy.mockClear();
  focusConsumedSpy.mockClear();
  setFeatureStateSpy.mockClear();
  removeFeatureStateSpy.mockClear();
  mapboxMocks.PopupMock.instances = [];
  mapboxMocks.MapMock.autoLoadDefault = true;
  mapboxMocks.MapMock.styleLoadedDefault = true;
  window.location.hash = "";
});

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("MapView focus handling", () => {
  it("waits for move, keeps tooltip, and consumes focus afterwards", async () => {
    const header = document.createElement("div");
    header.dataset.header = "true";
    Object.defineProperty(header, "offsetHeight", { value: 80, configurable: true });
    document.body.appendChild(header);

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="1"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
      await Promise.resolve();
    });

    await flush();
    const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1]!;
    await act(async () => {
      mapInstance.trigger("moveend");
    });
    await flush();

    expect(easeToSpy).toHaveBeenCalledTimes(1);
    const call = easeToSpy.mock.calls[0][0];
    expect(call).toMatchObject({
      center: [SAMPLE[0].lng, SAMPLE[0].lat],
      padding: expect.objectContaining({
        top: expect.any(Number),
        bottom: expect.any(Number),
      }),
    });
    expect(call.padding.top).toBeGreaterThanOrEqual(80 + Math.floor(600 * 0.1));
    expect(highlightSpy).toHaveBeenCalledWith("1");
    expect(openDetailSpy).not.toHaveBeenCalled();
    expect(focusConsumedSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId="1"
          detailId={null}
          focusId={null}
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    await flush();
    await act(async () => {
      mapInstance.trigger("moveend");
    });
    await flush();

    expect(PopupMock.instances.length).toBeGreaterThan(0);

    await act(async () => {
      mapInstance.trigger("idle");
    });
    await flush();
    const popupInstance = PopupMock.instances.find((popup) => popup.added);
    expect(popupInstance).toBeTruthy();
    expect(popupInstance?.lngLat).toEqual([SAMPLE[0].lng, SAMPLE[0].lat]);
    expect(popupInstance?.element.classList.contains("anchor-bottom")).toBe(true);

    header.remove();
  });

  it("does not crash when popup element is unavailable during first render cycle", async () => {
    const originalGetElement = mapboxMocks.PopupMock.prototype.getElement;
    let callCount = 0;
    mapboxMocks.PopupMock.prototype.getElement = function patchedGetElement(this: any) {
      callCount += 1;
      if (callCount === 1) {
        return undefined as any;
      }
      return originalGetElement.call(this);
    };

    try {
      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId={null}
            detailId={null}
            focusId="1"
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
        await flush();
      });

      const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1];
      expect(mapInstance).toBeTruthy();

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId="1"
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });

      await flush();

      expect(PopupMock.instances).toHaveLength(1);
      expect(highlightSpy).toHaveBeenCalledWith("1");
      await act(async () => {
        mapInstance?.trigger("moveend");
      });
      await flush();

      const popupInstance = PopupMock.instances.find((popup) => popup.added);
      expect(popupInstance).toBeTruthy();
    } finally {
      mapboxMocks.PopupMock.prototype.getElement = originalGetElement;
    }
  });

  it("reuses a single popup instance when highlight toggles", async () => {
    const originalFetch = globalThis.fetch;
    const fetchSpy = vi.fn();
    (globalThis as any).fetch = fetchSpy as any;

    try {
      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId={null}
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });
      await flush();

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId="1"
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });
      await flush();
      expect(PopupMock.instances).toHaveLength(1);
      const popupInstance = PopupMock.instances[0];
      expect(popupInstance.added).toBe(true);

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId={null}
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });
      await flush();
      expect(PopupMock.instances).toHaveLength(1);
      expect(popupInstance.added).toBe(false);

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId="1"
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });
      await flush();
      expect(PopupMock.instances).toHaveLength(1);
      expect(popupInstance.added).toBe(true);

      expect(fetchSpy).not.toHaveBeenCalled();
    } finally {
      if (originalFetch) {
        globalThis.fetch = originalFetch;
      } else {
        // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
        delete (globalThis as any).fetch;
      }
    }
  });

  it("switches tooltip immediately when selecting a different marker", async () => {
    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId="1"
          detailId={null}
          focusId={null}
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });
    await flush();
    expect(PopupMock.instances).toHaveLength(1);
    const popupInstance = PopupMock.instances[0];
    expect(popupInstance.added).toBe(true);
    expect(popupInstance.lngLat).toEqual([SAMPLE[0].lng, SAMPLE[0].lat]);

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId="2"
          detailId={null}
          focusId={null}
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });
    await flush();

    expect(popupInstance.added).toBe(true);
    expect(popupInstance.lngLat).toEqual([SAMPLE[1].lng, SAMPLE[1].lat]);
  });

  it("performs a single camera transition when clicking a marker", async () => {
    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId={null}
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });
    await flush();

    const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1]!;
    easeToSpy.mockClear();

    const markerLayerProps = markerLayerCapture.current;
    expect(markerLayerProps).toBeTruthy();

    await act(async () => {
      markerLayerProps?.onSelect?.("1");
      await flush();
    });

    await act(async () => {
      mapInstance.trigger("moveend");
    });
    await flush();

    expect(easeToSpy).toHaveBeenCalledTimes(1);
    const popupInstance = PopupMock.instances.find((popup) => popup.added);
    expect(popupInstance).toBeTruthy();
  });

  it("applies anchor class before animation frame runs", async () => {
    const originalRAF = globalThis.requestAnimationFrame;
    const rafCallbacks: FrameRequestCallback[] = [];
    globalThis.requestAnimationFrame = (cb: FrameRequestCallback) => {
      rafCallbacks.push(cb);
      return rafCallbacks.length;
    };

    try {
      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId={null}
            detailId={null}
            focusId="1"
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
        await flush();
      });

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId="1"
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });

      await flush();

      expect(PopupMock.instances.length).toBeGreaterThan(0);
      const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1]!;
      await act(async () => {
        mapInstance.trigger("moveend");
      });
      await flush();
      const popupInstance = PopupMock.instances.find((popup) => popup.added);
      expect(popupInstance).toBeTruthy();
      const el = popupInstance?.element;
      expect(el?.classList.contains("anchor-bottom") || el?.classList.contains("anchor-top")).toBe(true);
    } finally {
      rafCallbacks.splice(0).forEach((cb) => {
        try {
          cb(performance.now());
        } catch {
          /* ignore */
        }
      });
      globalThis.requestAnimationFrame = originalRAF;
    }
  });

  it("pans without reducing zoom when focusing while already on map", async () => {
    const header = document.createElement("div");
    header.dataset.header = "true";
    Object.defineProperty(header, "offsetHeight", { value: 40, configurable: true });
    document.body.appendChild(header);

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId="1"
          detailId={null}
          focusId={null}
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1]!;
    mapInstance.zoom = 14.5;
    mapInstance.bearing = 10;
    mapInstance.pitch = 5;
    mapInstance.project = () => ({ x: 400, y: 280 });

    easeToSpy.mockClear();

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="1"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    await flush();

    expect(easeToSpy).toHaveBeenCalledTimes(1);
    const call = easeToSpy.mock.calls[0][0];
    expect(call.zoom).toBeGreaterThanOrEqual(14.5);
    expect(call.padding.top).toBeGreaterThanOrEqual(40 + Math.floor(600 * 0.1));
    expect(call.duration).toBeGreaterThanOrEqual(450);

    header.remove();
  });

  it("clears focus hash after consumption and allows refocus", async () => {
    window.location.hash = "#/?view=map&focus=1";

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="1"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={() => {
            window.location.hash = "#/?view=map";
            focusConsumedSpy();
          }}
        />,
      );
    });

    await flush();

    expect(focusConsumedSpy).toHaveBeenCalled();
    expect(window.location.hash.includes("focus=")).toBe(false);

    easeToSpy.mockClear();
    highlightSpy.mockClear();

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="2"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    await flush();

    const popupInstance = PopupMock.instances[0];
    expect(popupInstance.lngLat).toEqual([SAMPLE[1].lng, SAMPLE[1].lat]);
  });

  it("queues focus until the map finishes loading", async () => {
    MapMock.autoLoadDefault = false;
    MapMock.styleLoadedDefault = false;

    try {
      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId={null}
            detailId={null}
            focusId="1"
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });

      await flush();

      expect(PopupMock.instances.every((popup) => popup.added === false)).toBe(true);

      const mapInstance = mapboxMocks.MapMock.instances[mapboxMocks.MapMock.instances.length - 1]!;
      mapInstance.styleLoaded = true;
      await act(async () => {
        mapInstance.trigger("load");
      });

      await flush();

      await act(async () => {
        root.render(
          <MapView
            locations={SAMPLE}
            highlightedId="1"
            detailId={null}
            focusId={null}
            onHighlight={highlightSpy}
            onOpenDetail={openDetailSpy}
            onFocusConsumed={focusConsumedSpy}
          />,
        );
      });

      await flush();

      await act(async () => {
        mapInstance.trigger("moveend");
      });
      await flush();
      const popupInstance = PopupMock.instances.find((popup) => popup.added);
      expect(popupInstance).toBeTruthy();
      expect(popupInstance?.lngLat).toEqual([SAMPLE[0].lng, SAMPLE[0].lat]);
      const element = popupInstance?.element;
      expect(
        element?.classList.contains("anchor-bottom") || element?.classList.contains("anchor-top"),
      ).toBe(true);
    } finally {
      MapMock.autoLoadDefault = true;
      MapMock.styleLoadedDefault = true;
    }
  });

  it("does not synchronously unmount popup root when navigating away", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await act(async () => {
      root.render(
        <MapView
          locations={SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="1"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    await act(async () => {
      root.render(<div>List view</div>);
    });

    await flush();

    expect(
      errorSpy.mock.calls.some(([message]) =>
        typeof message === "string" && message.includes("Attempted to synchronously unmount a root"),
      ),
    ).toBe(false);

    errorSpy.mockRestore();
  });

  it("ignores focus requests with invalid coordinates", async () => {
    const INVALID_SAMPLE: LocationMarker[] = [
      {
        ...SAMPLE[0],
        id: "invalid",
        lat: Number.NaN,
        lng: Number.NaN,
      },
    ];

    await act(async () => {
      root.render(
        <MapView
          locations={INVALID_SAMPLE}
          highlightedId={null}
          detailId={null}
          focusId="invalid"
          onHighlight={highlightSpy}
          onOpenDetail={openDetailSpy}
          onFocusConsumed={focusConsumedSpy}
        />,
      );
    });

    await flush();

    expect(easeToSpy).not.toHaveBeenCalled();
    expect(PopupMock.instances.every((popup) => popup.added === false)).toBe(true);
  });
});


import React, { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { LocationMarker } from "@/api/fetchLocations";

const mapLocationsHistory: LocationMarker[][] = [];
const listLocationsHistory: LocationMarker[][] = [];
const mapFocusHistory: Array<{ focusId: string | null; highlighted: string | null; detailed: string | null }> = [];
const filterRenderHistory: Array<{ mode: string | undefined; search: string }> = [];
const latestFiltersProps: { current: any } = { current: null };
const latestLocationListProps: { current: any } = { current: null };
const latestMapProps: { current: any } = { current: null };

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock("@/components/MapView", () => ({
  __esModule: true,
  default: (props: any) => {
    useEffect(() => {
      props.onViewportChange?.(null);
    }, [props.onViewportChange]);

    latestMapProps.current = props;

    useEffect(() => {
      if (!props.focusId) return;
      mapFocusHistory.push({
        focusId: props.focusId,
        highlighted: props.focusId,
        detailed: null,
      });
      props.onHighlight?.(props.focusId);
      props.onFocusConsumed?.();
    }, [props.focusId]);

    useEffect(() => {
      if (props.highlightedId == null && props.detailId == null) return;
      mapFocusHistory.push({
        focusId: props.focusId ?? null,
        highlighted: props.highlightedId ?? null,
        detailed: props.detailId ?? null,
      });
    }, [props.focusId, props.highlightedId, props.detailId]);

    mapLocationsHistory.push(props.locations);
    return React.createElement("div", { "data-testid": "map-view", "data-count": props.locations.length });
  },
}));

vi.mock("@/components/LocationList", () => ({
  __esModule: true,
  default: (props: any) => {
    listLocationsHistory.push(props.locations);
    latestLocationListProps.current = props;
    return React.createElement(
      "div",
      { "data-testid": "location-list", "data-count": props.locations.length },
      props.locations.map((loc: LocationMarker) =>
        React.createElement(
          "button",
          {
            key: loc.id,
            type: "button",
            "data-testid": `show-${loc.id}`,
            onClick: () => props.onShowOnMap?.(loc.id),
          },
          `Show ${loc.id}`,
        ),
      ),
    );
  },
}));

vi.mock("@/components/BottomSheet", () => ({
  __esModule: true,
  default: ({ children }: any) => React.createElement("div", { "data-testid": "bottom-sheet" }, children),
}));

vi.mock("@/components/LocationDetail", () => ({
  __esModule: true,
  default: ({ location }: any) =>
    React.createElement("div", { "data-testid": "location-detail", "data-id": location?.id }),
}));

vi.mock("@/components/OverlayDetailCard", () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock("@/components/Filters", () => ({
  __esModule: true,
  default: (props: any) => {
    latestFiltersProps.current = props;
    filterRenderHistory.push({ mode: props.viewMode, search: props.search ?? "" });
    return React.createElement(
      "div",
      { "data-testid": "filters" },
      [
        React.createElement("input", {
          key: "search",
          name: "search",
          value: props.search ?? "",
          onChange: (event: any) => props.onChange?.({ search: event?.target?.value ?? "" }),
        }),
        React.createElement("button", {
          key: "map",
          type: "button",
          "data-view": "map",
          onClick: () => props.onViewModeChange?.("map"),
        }, "Map"),
        React.createElement("button", {
          key: "list",
          type: "button",
          "data-view": "list",
          onClick: () => props.onViewModeChange?.("list"),
        }, "List"),
      ],
    );
  },
}));

const { fetchLocationsMock, fetchLocationsCountMock } = vi.hoisted(() => ({
  fetchLocationsMock: vi.fn(),
  fetchLocationsCountMock: vi.fn(),
}));

vi.mock("@/api/fetchLocations", async () => {
  const actual = await vi.importActual<any>("@/api/fetchLocations");
  return {
    ...actual,
    fetchLocations: fetchLocationsMock,
    fetchLocationsCount: fetchLocationsCountMock,
  };
});

import App from "@/App";

const SAMPLE_LOCATIONS: LocationMarker[] = [
  {
    id: "1",
    name: "Istanbul Market",
    category: "supermarket",
    state: "VERIFIED",
    is_turkish: true,
    rating: null,
    confidence_score: 0.95,
    lat: 51.92,
    lng: 4.47,
  },
  {
    id: "2",
    name: "Baklava House",
    category: "bakery",
    state: "VERIFIED",
    is_turkish: true,
    rating: null,
    confidence_score: 0.91,
    lat: 51.93,
    lng: 4.48,
  },
] as LocationMarker[];

let container: HTMLDivElement;
let root: Root;

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: /min-width: 1024px/.test(query),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

beforeEach(() => {
  vi.useFakeTimers();
  mapLocationsHistory.length = 0;
  listLocationsHistory.length = 0;
  mapFocusHistory.length = 0;
  filterRenderHistory.length = 0;
  latestFiltersProps.current = null;
  latestLocationListProps.current = null;
  latestMapProps.current = null;
  fetchLocationsMock.mockReset();
  fetchLocationsCountMock.mockReset();
  fetchLocationsMock.mockResolvedValue(SAMPLE_LOCATIONS);
  fetchLocationsCountMock.mockResolvedValue(SAMPLE_LOCATIONS.length);

  window.location.hash = "#/";

  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.useRealTimers();
  vi.clearAllMocks();
});

async function flushAllTimers() {
  await act(async () => {
    vi.runAllTimers();
  });
  await act(async () => Promise.resolve());
}

async function renderApp() {
  await act(async () => {
    root.render(React.createElement(App));
  });
}

async function clickView(view: "map" | "list") {
  const target = container.querySelector(`button[data-view="${view}"]`);
  expect(target).toBeTruthy();
  await act(async () => {
    target!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

async function clickShowOnMap(id: string) {
  const button = container.querySelector(`button[data-testid="show-${id}"]`);
  expect(button).toBeTruthy();
  await act(async () => {
    button!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

describe("List/Map view modes", () => {
  it("preserves filters and avoids duplicate fetches when toggling views", async () => {
    await renderApp();
    await flushAllTimers();

    expect(fetchLocationsCountMock).toHaveBeenCalledTimes(1);
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      latestFiltersProps.current?.onChange?.({ search: "bak" });
    });

    await flushAllTimers();

    await clickView("list");

    await flushAllTimers();

    expect(window.location.hash).toContain("view=list");
    const mapSearches = filterRenderHistory.filter((entry) => entry.mode === "map").map((entry) => entry.search);
    expect(mapSearches).toContain("bak");
    const listSearches = filterRenderHistory.filter((entry) => entry.mode === "list").map((entry) => entry.search);
    expect(listSearches).toContain("bak");
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);
    expect(fetchLocationsCountMock).toHaveBeenCalledTimes(1);
    const latestMap = mapLocationsHistory[mapLocationsHistory.length - 1];
    const latestList = listLocationsHistory[listLocationsHistory.length - 1];
    const latestMapCount = latestMap?.length ?? 0;
    expect(latestList?.length).toBe(latestMapCount);

    await clickShowOnMap("2");
    await flushAllTimers();

    expect(window.location.hash).toContain("view=map");
    expect(window.location.hash).not.toContain("focus=");
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);
    expect(fetchLocationsCountMock).toHaveBeenCalledTimes(1);
    const focusEntry = mapFocusHistory.find((entry) => entry.focusId === "2" && entry.highlighted === "2");
    expect(focusEntry).toBeTruthy();
    expect(focusEntry?.detailed).toBeNull();

    await act(async () => {
      latestMapProps.current?.onHighlight?.("1");
    });

    await flushAllTimers();

    expect(window.location.hash).toContain("view=map");
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);
    const markerEntry = mapFocusHistory.find(
      (entry) => entry.focusId === null && entry.highlighted === "1"
    );
    expect(markerEntry).toBeTruthy();
    expect(markerEntry?.detailed).toBeNull();
  });

  it("restores camera when returning to map without focus", async () => {
    await renderApp();
    await flushAllTimers();

    await act(async () => {
      latestMapProps.current?.onViewportChange?.("1,2,3,4");
    });

    await flushAllTimers();

    await clickView("list");
    await flushAllTimers();

    await clickView("map");
    await flushAllTimers();

    expect(fetchLocationsMock).toHaveBeenCalledTimes(2);
    expect(mapLocationsHistory.length).toBeGreaterThan(1);
  });

  it("renders list view when deep-linked to #/?view=list", async () => {
    window.location.hash = "#/?view=list";
    await renderApp();
    await flushAllTimers();

    expect(container.querySelector('[data-testid="map-view"]')).toBeNull();
    expect(listLocationsHistory[listLocationsHistory.length - 1]?.length).toBe(SAMPLE_LOCATIONS.length);
  });

  it("renders map view when deep-linked to #/?view=map", async () => {
    window.location.hash = "#/?view=map";
    await renderApp();
    await flushAllTimers();

    expect(container.querySelector('[data-testid="map-view"]')).toBeTruthy();
  });

  it("reacts to external hash changes without refetching", async () => {
    window.location.hash = "#/?view=map";
    await renderApp();
    await flushAllTimers();

    expect(container.querySelector('[data-testid="map-view"]')).toBeTruthy();
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      window.location.hash = "#/?view=list";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await flushAllTimers();

    expect(container.querySelector('[data-testid="map-view"]')).toBeNull();
    expect(listLocationsHistory[listLocationsHistory.length - 1]?.length).toBe(SAMPLE_LOCATIONS.length);
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      window.location.hash = "#/?view=map";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });

    await flushAllTimers();

    expect(container.querySelector('[data-testid="map-view"]')).toBeTruthy();
    expect(fetchLocationsMock).toHaveBeenCalledTimes(1);
    expect(mapLocationsHistory.length).toBeGreaterThan(1);
  });
});



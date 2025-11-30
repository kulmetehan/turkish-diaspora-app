
// src/components/MapView.tsx
import mapboxgl, { Map as MapboxMap, type GeoJSONSource, type LngLatLike } from "mapbox-gl";
import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { createRoot, type Root } from "react-dom/client";
import type { FeatureCollection, Point } from "geojson";

import type { LocationMarker } from "@/api/fetchLocations";
import MapControls from "@/components/MapControls";
import { restoreCamera, storeCamera } from "@/components/mapCameraCache";
import { MARKER_POINT_OUTER_RADIUS, MarkerLayerIds, registerClusterSprites, ensureBaseLayers } from "@/components/markerLayerUtils";
import PreviewTooltip from "@/components/PreviewTooltip";
import { cn } from "@/lib/ui/cn";
import { CONFIG, CLUSTER_CONFIG } from "@/lib/config";
import MarkerLayer from "./MarkerLayer";
import { attachCategoryIconFallback, ensureCategoryIcons } from "@/lib/map/categoryIcons";
import { useViewportContext } from "@/contexts/viewport";
import { useInitialMapCenter } from "@/hooks/useInitialMapCenter";
import { clearCamera } from "@/components/mapCameraCache";
import { computeInitialUnclusteredView } from "@/lib/initialView";
import { isMobile } from "@/lib/utils";

// Zorg dat je VITE_MAPBOX_TOKEN in .env staat
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

type Props = {
  locations: LocationMarker[];
  globalLocations?: LocationMarker[]; // NEW: entire global dataset for lookup
  highlightedId: string | null;
  detailId: string | null;
  onHighlight?: (id: string | null) => void;
  onOpenDetail?: (id: string) => void;
  onMapClick?: () => void;
  onViewportChange?: (bbox: string | null) => void;
  interactionDisabled?: boolean;
  focusId?: string | null;
  onFocusConsumed?: () => void;
  centerOnSelect?: boolean;
  onSuppressNextViewportFetch?: () => void;
};

const TOOLTIP_POINTER_HEIGHT = MARKER_POINT_OUTER_RADIUS;
const POPUP_OFFSET: mapboxgl.PopupOptions["offset"] = {
  top: [0, TOOLTIP_POINTER_HEIGHT],
  "top-left": [0, TOOLTIP_POINTER_HEIGHT],
  "top-right": [0, TOOLTIP_POINTER_HEIGHT],
  bottom: [0, -MARKER_POINT_OUTER_RADIUS],
  "bottom-left": [0, -MARKER_POINT_OUTER_RADIUS],
  "bottom-right": [0, -MARKER_POINT_OUTER_RADIUS],
  left: [MARKER_POINT_OUTER_RADIUS, -MARKER_POINT_OUTER_RADIUS],
  right: [-MARKER_POINT_OUTER_RADIUS, -MARKER_POINT_OUTER_RADIUS],
};
type UserLocationProperties = {
  accuracy?: number;
  latRadians: number;
};

const FOCUS_BIAS_RATIO = 0.15;
type EaseOptions = Parameters<MapboxMap["easeTo"]>[0];
const MY_LOCATION_ZOOM = CONFIG.MAP_MY_LOCATION_ZOOM ?? 14;
const USER_LOCATION_SOURCE_ID = "tda-user-location";
const USER_LOCATION_ACCURACY_LAYER_ID = "tda-user-location-accuracy";
const USER_LOCATION_DOT_LAYER_ID = "tda-user-location-dot";
const EARTH_METERS_PER_PIXEL_AT_EQUATOR = 156543.03392;
const MAX_ACCURACY_RADIUS = 400;
const EMPTY_FEATURE_COLLECTION: FeatureCollection<Point, UserLocationProperties> = {
  type: "FeatureCollection",
  features: [],
};

function safeHasLayer(map: any, id: string) {
  try {
    return Boolean(map?.getLayer?.(id));
  } catch {
    return false;
  }
}

function metersToPixelsAtLatitude(lat: number, meters: number, zoom: number): number {
  if (!Number.isFinite(lat) || !Number.isFinite(meters) || !Number.isFinite(zoom) || meters <= 0) {
    return 0;
  }
  const cosLat = Math.cos((lat * Math.PI) / 180);
  if (!Number.isFinite(cosLat) || cosLat <= 0) {
    return 0;
  }
  const pixels = (meters / (EARTH_METERS_PER_PIXEL_AT_EQUATOR * cosLat)) * Math.pow(2, zoom);
  if (!Number.isFinite(pixels) || pixels <= 0) {
    return 0;
  }
  return Math.min(MAX_ACCURACY_RADIUS, pixels);
}

const defer = (fn: () => void) => {
  if (typeof queueMicrotask === "function") {
    queueMicrotask(() => {
      try {
        fn();
      } catch {
        /* ignore */
      }
    });
  } else {
    setTimeout(() => {
      try {
        fn();
      } catch {
        /* ignore */
      }
    }, 0);
  }
};

const isFiniteCoord = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

type PopupControllerParams = {
  id: string;
  location: LocationMarker;
  onRequestClose: () => void;
  onRequestDetail: () => void;
};

type PopupController = {
  showFor: (params: PopupControllerParams) => void;
  switchTo: (params: PopupControllerParams) => void;
  hide: () => void;
  updateAnchor: () => void;
  currentId: () => string | null;
  isVisible: () => boolean;
};

function usePopupController(
  mapRef: MutableRefObject<MapboxMap | null>,
  mapReady: boolean,
  destroyedRef: MutableRefObject<boolean>,
): PopupController {
  const stateRef = useRef<{
    popup: mapboxgl.Popup;
    root: Root;
    container: HTMLElement;
    id: string | null;
    lngLat: [number, number] | null;
    visible: boolean;
    rafId: number | null;
  } | null>(null);
  const popupInitRef = useRef(false);
  const waitingForStyleRef = useRef(false);
  const rafIdsRef = useRef<Set<number>>(new Set());

  const ensurePopup = useCallback(() => {
    if (destroyedRef.current) return;
    if (stateRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const isStyleLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
    if (!isStyleLoaded) {
      if (waitingForStyleRef.current) return;
      waitingForStyleRef.current = true;
      const handleStyle = () => {
        waitingForStyleRef.current = false;
        try {
          map.off("styledata", handleStyle);
        } catch {
          /* ignore */
        }
        ensurePopup();
      };
      try {
        map.once("styledata", handleStyle);
      } catch {
        map.on("styledata", handleStyle);
      }
      return;
    }

    if (popupInitRef.current) return;
    popupInitRef.current = true;

    const container = document.createElement("div");
    const root = createRoot(container);
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      offset: POPUP_OFFSET,
      anchor: "bottom",
      className: "tda-preview-popup",
    })
      .setDOMContent(container)
      .setMaxWidth("0");

    const element = popup.getElement?.();
    if (element?.classList) {
      element.classList.add("tda-preview-popup");
    }

    stateRef.current = {
      popup,
      root,
      container,
      id: null,
      lngLat: null,
      visible: false,
      rafId: null,
    };

    popup.on("close", () => {
      const current = stateRef.current;
      if (!current) return;
      current.visible = false;
      current.id = null;
      current.lngLat = null;
      // IMPORTANT: make this synchronous to avoid race conditions
      try {
        current.root.render(null);
      } catch {
        /* ignore */
      }
    });
  }, [destroyedRef, mapRef]);

  const updateAnchor = useCallback(() => {
    if (destroyedRef.current) return;
    const map = mapRef.current;
    const current = stateRef.current;
    if (!map || !current || !current.visible || !current.lngLat) return;

    const element = current.popup.getElement?.();
    if (!element) return;
    const card = element.querySelector(".tda-card") as HTMLElement | null;
    const content = element.querySelector(".mapboxgl-popup-content") as HTMLElement | null;
    if (!card || !content) return;

    const canvas = map.getCanvas();
    const vw = canvas.clientWidth;
    const vh = canvas.clientHeight;
    const point = map.project(current.lngLat);

    const rect = card.getBoundingClientRect();
    const { width, height } = rect;

    const margin = 12;
    const offsetY = TOOLTIP_POINTER_HEIGHT + MARKER_POINT_OUTER_RADIUS;

    let anchor: "top" | "bottom" = "bottom";
    if (point.y - offsetY - height < margin) {
      anchor = "top";
    } else if (point.y + offsetY + height > vh - margin) {
      anchor = "bottom";
    }

    let shiftX = 0;
    const half = width / 2;
    if (point.x - half < margin) {
      shiftX = half - point.x + margin;
    } else if (point.x + half > vw - margin) {
      shiftX = -(point.x + half - vw + margin);
    }

    element.classList.toggle("anchor-top", anchor === "top");
    element.classList.toggle("anchor-bottom", anchor === "bottom");
    content.style.transform = `translateX(${Math.round(shiftX)}px)`;
  }, [destroyedRef, mapRef]);

  const scheduleUpdate = useCallback(() => {
    if (destroyedRef.current) return;
    const current = stateRef.current;
    if (!current) return;
    if (current.rafId != null) {
      cancelAnimationFrame(current.rafId);
      rafIdsRef.current.delete(current.rafId);
    }
    current.rafId = requestAnimationFrame(() => {
      rafIdsRef.current.delete(current.rafId as number);
      current.rafId = null;
      updateAnchor();
    });
    if (current.rafId != null) {
      rafIdsRef.current.add(current.rafId);
    }
  }, [destroyedRef, updateAnchor]);

  const showFor = useCallback(
    ({ id, location, onRequestClose, onRequestDetail }: PopupControllerParams) => {
      if (destroyedRef.current) return;
      const map = mapRef.current;
      if (!map || !isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) return;

      ensurePopup();
      const current = stateRef.current;
      if (!current) return;

      const nextLngLat: [number, number] = [location.lng, location.lat];
      const isSameTarget = current.id === id && current.visible;

      current.id = id;
      current.lngLat = nextLngLat;

      current.root.render(
        <PreviewTooltip
          location={location}
          onRequestClose={() => {
            onRequestClose();
          }}
          onRequestDetail={() => {
            onRequestDetail();
          }}
        />,
      );

      if (!isSameTarget) {
        current.popup.setLngLat(nextLngLat);
        current.popup.addTo(map);
      } else {
        current.popup.setLngLat(nextLngLat);
      }

      const element = current.popup.getElement?.();
      const mapLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
      const canvas = map.getCanvas();
      const vw = canvas.clientWidth;
      const vh = canvas.clientHeight;
      const point = mapLoaded ? map.project(nextLngLat) : { x: vw / 2, y: vh / 2 };
      let immediateAnchor: "top" | "bottom" = "bottom";
      const margin = 12;
      const expoHeight = MARKER_POINT_OUTER_RADIUS + TOOLTIP_POINTER_HEIGHT + margin;
      if (point.y - expoHeight < margin) {
        immediateAnchor = "top";
      } else if (point.y + expoHeight > vh - margin) {
        immediateAnchor = "bottom";
      }

      current.visible = true;
      if (element?.classList) {
        element.classList.remove("anchor-top", "anchor-bottom", "anchor-left", "anchor-right");
        element.classList.add(immediateAnchor === "top" ? "anchor-top" : "anchor-bottom");
      }
      scheduleUpdate();
    },
    [destroyedRef, ensurePopup, scheduleUpdate],
  );

  const hide = useCallback(() => {
    if (destroyedRef.current) return;
    const current = stateRef.current;
    if (!current || !current.visible) return;
    current.visible = false;
    current.id = null;
    current.lngLat = null;
    defer(() => {
      try {
        current.root.render(null);
      } catch {
        /* ignore */
      }
    });
    try {
      current.popup.remove();
    } catch {
      /* ignore */
    }
  }, [destroyedRef]);

  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    ensurePopup();

    const events = ["move", "moveend", "idle", "resize", "zoom", "pitch"] as const;
    const handler = () => scheduleUpdate();

    events.forEach((event) => {
      map.on(event, handler as any);
    });

    map.on("styledata", handler as any);

    return () => {
      events.forEach((event) => {
        try {
          map.off(event, handler as any);
        } catch {
          /* ignore */
        }
      });
      try {
        map.off("styledata", handler as any);
      } catch {
        /* ignore */
      }
    };
  }, [destroyedRef, ensurePopup, mapReady, mapRef, scheduleUpdate]);

  useEffect(() => {
    return () => {
      rafIdsRef.current.forEach((id) => cancelAnimationFrame(id));
      rafIdsRef.current.clear();
      const current = stateRef.current;
      if (!current) {
        popupInitRef.current = false;
        waitingForStyleRef.current = false;
        stateRef.current = null;
        return;
      }
      if (current.rafId != null) {
        cancelAnimationFrame(current.rafId);
      }
      defer(() => {
        try {
          current.root.unmount();
        } catch {
          /* ignore */
        }
      });
      try {
        current.popup.remove();
      } catch {
        /* ignore */
      }
      popupInitRef.current = false;
      waitingForStyleRef.current = false;
      stateRef.current = null;
    };
  }, []);

  const switchTo = useCallback(
    (params: PopupControllerParams) => {
      if (destroyedRef.current) return;
      const map = mapRef.current;
      if (!map) return;
      ensurePopup();
      const current = stateRef.current;
      if (!current) return;

      const previousId = current.id;
      const wasVisible = current.visible;
      if (wasVisible && previousId && previousId !== params.id) {
        current.visible = false;
        try {
          current.popup.remove();
        } catch {
          /* ignore */
        }
      }

      showFor(params);
      updateAnchor();
      scheduleUpdate();
    },
    [destroyedRef, ensurePopup, scheduleUpdate, showFor, updateAnchor],
  );

  const currentId = useCallback(() => stateRef.current?.id ?? null, []);
  const isVisible = useCallback(() => Boolean(stateRef.current?.visible), []);

  return useMemo(
    () => ({
      showFor,
      switchTo,
      hide,
      updateAnchor: scheduleUpdate,
      currentId,
      isVisible,
    }),
    [currentId, hide, isVisible, scheduleUpdate, showFor, switchTo],
  );
}

/**
 * MapView: toont de Mapbox-kaart en de MarkerLayer.
 * - Houdt één map-instantie in leven
 * - Laat de gebruiker zelf de viewport beheren (geen auto-centering)
 */
export default function MapView({
  locations,
  globalLocations,
  highlightedId,
  detailId,
  onHighlight,
  onOpenDetail,
  onMapClick,
  onViewportChange,
  interactionDisabled = false,
  focusId,
  onFocusConsumed,
  centerOnSelect = true,
  onSuppressNextViewportFetch,
}: Props) {
  const { setViewport } = useViewportContext();
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const lastBboxRef = useRef<string | null>(null);
  const lastFocusRef = useRef<string | null>(null);
  const focusPendingRef = useRef<{ id: string; cancel: () => void } | null>(null);
  const allLocationsRef = useRef<LocationMarker[]>(locations);
  const globalLocationsRef = useRef<LocationMarker[]>([]);
  const destroyedRef = useRef(false);
  const pendingFocusDataRef = useRef<{ id: string; location: LocationMarker } | null>(null);
  const mapEventCleanupRef = useRef<(() => void)[]>([]);
  const cameraBusyRef = useRef(false);
  const transitionCleanupRef = useRef<(() => void) | null>(null);
  const viewportDebounceRef = useRef<number | null>(null);
  const popup = usePopupController(mapRef, mapReady, destroyedRef);
  const onMapClickRef = useRef(onMapClick);
  const [isLocating, setIsLocating] = useState(false);
  const userLocationDataRef = useRef<FeatureCollection<Point, UserLocationProperties>>(EMPTY_FEATURE_COLLECTION);
  const userLocationPaintRef = useRef<{ z10: number; z14: number; z18: number }>({ z10: 0, z14: 0, z18: 0 });
  const initialCenterResult = useInitialMapCenter();
  const initialCenterAppliedRef = useRef(false);
  const initialViewSettledRef = useRef(false);
  const initialViewAttemptedRef = useRef(false);

  const applyAccuracyPaint = useCallback(
    (targetMap: MapboxMap | null = mapRef.current) => {
      const map = targetMap;
      if (!map) return;
      if (!safeHasLayer(map, USER_LOCATION_ACCURACY_LAYER_ID)) return;
      const { z10, z14, z18 } = userLocationPaintRef.current;
      try {
        map.setPaintProperty(USER_LOCATION_ACCURACY_LAYER_ID, "circle-radius", [
          "interpolate",
          ["linear"],
          ["zoom"],
          10,
          z10,
          14,
          z14,
          18,
          z18,
        ]);
      } catch {
        /* ignore */
      }
    },
    [],
  );

  const clearUserLocation = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource(USER_LOCATION_SOURCE_ID) as GeoJSONSource | undefined;
    userLocationDataRef.current = {
      type: "FeatureCollection",
      features: [],
    };
    userLocationPaintRef.current = { z10: 0, z14: 0, z18: 0 };
    applyAccuracyPaint(map);
    source?.setData(userLocationDataRef.current);
  }, [applyAccuracyPaint]);

  const ensureUserLocationLayers = useCallback(() => {
    const map = mapRef.current;
    if (!map || destroyedRef.current) return false;

    if (!map.getSource(USER_LOCATION_SOURCE_ID)) {
      map.addSource(USER_LOCATION_SOURCE_ID, {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });
    }

    if (!safeHasLayer(map, USER_LOCATION_ACCURACY_LAYER_ID)) {
      try {
        const layerConfig = {
          id: USER_LOCATION_ACCURACY_LAYER_ID,
          type: "circle" as const,
          source: USER_LOCATION_SOURCE_ID,
          filter: ["==", ["geometry-type"], "Point"] as any,
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10,
              userLocationPaintRef.current.z10,
              14,
              userLocationPaintRef.current.z14,
              18,
              userLocationPaintRef.current.z18,
            ],
            "circle-color": "#38bdf8",
            "circle-opacity": 0.18,
            "circle-stroke-width": 0,
          },
        };
        // Defensive: check if marker layer exists before using as beforeId
        // Prevents race condition error when maintainLayers runs before marker layers are created
        if (safeHasLayer(map, MarkerLayerIds.L_POINT)) {
          map.addLayer(layerConfig, MarkerLayerIds.L_POINT);
        } else {
          map.addLayer(layerConfig);
        }
        applyAccuracyPaint(map);
      } catch {
        /* ignore layering errors */
      }
    }

    if (!safeHasLayer(map, USER_LOCATION_DOT_LAYER_ID)) {
      try {
        const layerConfig = {
          id: USER_LOCATION_DOT_LAYER_ID,
          type: "circle" as const,
          source: USER_LOCATION_SOURCE_ID,
          filter: ["==", ["geometry-type"], "Point"] as any,
          paint: {
            "circle-color": "#0284c7",
            "circle-opacity": 1,
            "circle-radius": 6,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
          },
        };
        if (safeHasLayer(map, MarkerLayerIds.L_POINT)) {
          map.addLayer(layerConfig, MarkerLayerIds.L_POINT);
        } else {
          map.addLayer(layerConfig);
        }
      } catch {
        /* ignore layering errors */
      }
    }

    return true;
  }, [applyAccuracyPaint, destroyedRef]);

  const removeUserLocationLayers = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    try {
      if (map.getLayer(USER_LOCATION_DOT_LAYER_ID)) {
        map.removeLayer(USER_LOCATION_DOT_LAYER_ID);
      }
      if (map.getLayer(USER_LOCATION_ACCURACY_LAYER_ID)) {
        map.removeLayer(USER_LOCATION_ACCURACY_LAYER_ID);
      }
      if (map.getSource(USER_LOCATION_SOURCE_ID)) {
        map.removeSource(USER_LOCATION_SOURCE_ID);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const setUserLocation = useCallback(
    (lng: number, lat: number, accuracy?: number | null) => {
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        clearUserLocation();
        return;
      }
      const map = mapRef.current;
      if (!map || destroyedRef.current) return;

      const layersReady = ensureUserLocationLayers();
      if (!layersReady) return;

      const featureCollection: FeatureCollection<Point, UserLocationProperties> = {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Point",
              coordinates: [lng, lat],
            },
            properties: {
              accuracy: typeof accuracy === "number" && accuracy > 0 ? accuracy : undefined,
              latRadians: (lat * Math.PI) / 180,
            },
          },
        ],
      };

      userLocationDataRef.current = featureCollection;
      const stops =
        typeof accuracy === "number" && accuracy > 0
          ? {
              z10: metersToPixelsAtLatitude(lat, accuracy, 10),
              z14: metersToPixelsAtLatitude(lat, accuracy, 14),
              z18: metersToPixelsAtLatitude(lat, accuracy, 18),
            }
          : { z10: 0, z14: 0, z18: 0 };
      userLocationPaintRef.current = stops;
      applyAccuracyPaint(map);

    const source = map.getSource(USER_LOCATION_SOURCE_ID) as GeoJSONSource | undefined;
      source?.setData(featureCollection);
    },
    [applyAccuracyPaint, clearUserLocation, destroyedRef, ensureUserLocationLayers],
  );
  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const maintainLayers = () => {
      ensureUserLocationLayers();
      applyAccuracyPaint(map);
      const source = map.getSource(USER_LOCATION_SOURCE_ID) as GeoJSONSource | undefined;
      if (source && typeof source.setData === "function" && userLocationDataRef.current) {
        source.setData(userLocationDataRef.current);
      }
    };

    maintainLayers();
    map.on("styledata", maintainLayers);

    return () => {
      try {
        map.off("styledata", maintainLayers);
      } catch {
        /* ignore */
      }
    };
  }, [applyAccuracyPaint, destroyedRef, ensureUserLocationLayers, mapReady]);

  useEffect(() => {
    onMapClickRef.current = onMapClick;
  }, [onMapClick]);

  const findLocationById = useCallback((id: string | number | null | undefined) => {
    if (id == null) return null;
    const key = String(id);
    
    // 1) Try currently rendered/filtered locations first
    const fromRendered = allLocationsRef.current.find(
      (loc) => String(loc.id) === key
    );
    if (fromRendered) return fromRendered;
    
    // 2) Fallback to global dataset
    const fromGlobal = globalLocationsRef.current.find(
      (loc) => String(loc.id) === key
    );
    if (fromGlobal) return fromGlobal;
    
    return null;
  }, []);

  const switchPopupToLocation = useCallback(
    (location: LocationMarker) => {
      if (destroyedRef.current) return;
      if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
        return;
      }
      popup.switchTo({
        id: String(location.id),
        location,
        onRequestClose: () => {
          onHighlight?.(null);
        },
        onRequestDetail: () => {
          onOpenDetail?.(location.id);
        },
      });
    },
    [destroyedRef, onHighlight, onOpenDetail, popup],
  );

  const hidePopup = useCallback(() => {
    popup.hide();
  }, [popup]);

  const isMapFullyLoaded = useCallback((mapInstance?: MapboxMap | null) => {
    const map = mapInstance ?? mapRef.current;
    if (!map) return false;
    const styleLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
    if (!styleLoaded) return false;
    const loadedValue = (map as any)?.loaded;
    const loaded = typeof loadedValue === "function" ? loadedValue.call(map) : loadedValue;
    return Boolean(styleLoaded && (loaded === undefined || loaded === true));
  }, []);

  // Notify parent about viewport changes (bbox) when map stops moving
  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    const map = mapRef.current;
    if (!map) return;

    const emit = (bbox: string | null) => {
      if (!onViewportChange) return;
      if (viewportDebounceRef.current !== null) {
        window.clearTimeout(viewportDebounceRef.current);
      }
      viewportDebounceRef.current = window.setTimeout(() => {
        viewportDebounceRef.current = null;
        if (lastBboxRef.current === bbox) return;
        lastBboxRef.current = bbox;
        onViewportChange(bbox);
      }, 250);
    };

    const handle = () => {
      try {
        const zoomValue = typeof map.getZoom === "function" ? map.getZoom() : null;
        const center = map.getCenter?.();
        const centerLat =
          center && typeof (center as any).lat === "number" && Number.isFinite((center as any).lat)
            ? (center as any).lat
            : null;
        const centerLng =
          center && typeof (center as any).lng === "number" && Number.isFinite((center as any).lng)
            ? (center as any).lng
            : null;

        const bounds = map.getBounds?.();
        let nextBbox: string | null = null;
        let visibleSamples: { city?: string | null }[] | null = null;

        if (bounds) {
          const sw = bounds.getSouthWest?.();
          const ne = bounds.getNorthEast?.();
          const hasValidCorners =
            sw &&
            ne &&
            typeof sw.lng === "number" &&
            typeof sw.lat === "number" &&
            typeof ne.lng === "number" &&
            typeof ne.lat === "number";

          if (hasValidCorners) {
            const isZoomedOut =
              typeof zoomValue === "number" &&
              (zoomValue <= 2 || (ne.lng - sw.lng) > 180 || (ne.lat - sw.lat) > 90);
            nextBbox = isZoomedOut ? null : `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`;

            const minLng = Math.min(sw.lng, ne.lng);
            const maxLng = Math.max(sw.lng, ne.lng);
            const minLat = Math.min(sw.lat, ne.lat);
            const maxLat = Math.max(sw.lat, ne.lat);

            const samples = allLocationsRef.current.filter((loc) => {
              if (!isFiniteCoord(loc.lng) || !isFiniteCoord(loc.lat)) return false;
              return (
                loc.lng! >= minLng &&
                loc.lng! <= maxLng &&
                loc.lat! >= minLat &&
                loc.lat! <= maxLat
              );
            });

            if (samples.length > 0) {
              visibleSamples = samples.map((loc) => ({ city: loc.city ?? null }));
            }
          }
        }

        setViewport({
          zoom: typeof zoomValue === "number" && Number.isFinite(zoomValue) ? zoomValue : null,
          centerLat,
          centerLng,
          visible: visibleSamples,
        });

        emit(nextBbox);
      } catch {
        setViewport({
          zoom: null,
          centerLat: null,
          centerLng: null,
          visible: null,
        });
        emit(null);
      }
    };

    // Only emit initial bbox if initial view is settled or we're using fallback
    const shouldEmitInitial = initialViewSettledRef.current || 
      (initialCenterResult.status === "resolved" && initialCenterResult.source === "fallback_city");
    
    if (shouldEmitInitial) {
      handle();
    }
    
    map.on("moveend", handle);

    return () => {
      if (viewportDebounceRef.current !== null) {
        window.clearTimeout(viewportDebounceRef.current);
        viewportDebounceRef.current = null;
      }
      try {
        map.off("moveend", handle);
      } catch {
        /* ignore */
      }
    };
  }, [destroyedRef, mapReady, onViewportChange, setViewport, initialCenterResult.status, initialCenterResult.source]);

  useEffect(() => {
    allLocationsRef.current = locations;
  }, [locations]);

  useEffect(() => {
    globalLocationsRef.current = globalLocations ?? [];
  }, [globalLocations]);

  const computeFocusPadding = useCallback(() => {
    const map = mapRef.current;
    if (typeof window === "undefined") {
      return { top: 0, bottom: 0, canvasHeight: 0 };
    }
    const header = document.querySelector("[data-header]");
    const filters = document.querySelector("[data-filters-overlay]");
    const bottomSheet = document.querySelector("[data-bottom-sheet]");

    const headerHeight = header instanceof HTMLElement ? header.offsetHeight : 0;
    const filtersHeight = filters instanceof HTMLElement ? filters.offsetHeight : 0;
    const bottomSheetHeight = bottomSheet instanceof HTMLElement ? bottomSheet.offsetHeight : 0;

    const canvas = map?.getCanvas();
    const vh = canvas?.clientHeight ?? window.innerHeight;
    const bias = Math.round(vh * FOCUS_BIAS_RATIO);

    return {
      top: headerHeight + filtersHeight + bias,
      bottom: bottomSheetHeight,
      canvasHeight: vh,
    };
  }, []);

  const stopActiveTransition = useCallback(() => {
    transitionCleanupRef.current?.();
    transitionCleanupRef.current = null;
    cameraBusyRef.current = false;
  }, []);

  const performCameraTransition = useCallback(
    (options: EaseOptions & { center: [number, number] }, onFinished?: () => void) => {
      const map = mapRef.current;
      if (!map || destroyedRef.current) return false;
      const [lng, lat] = options.center;
      if (!isFiniteCoord(lng) || !isFiniteCoord(lat)) return false;

      map.stop();
      stopActiveTransition();

      cameraBusyRef.current = true;

      const handleEnd = () => {
        cameraBusyRef.current = false;
        if (transitionCleanupRef.current === cleanup) {
          transitionCleanupRef.current = null;
        }
        onFinished?.();
      };

      const cleanup = () => {
        try {
          map.off("moveend", handleEnd);
        } catch {
          /* ignore */
        }
        transitionCleanupRef.current = null;
      };

      transitionCleanupRef.current = cleanup;

      try {
        map.once("moveend", handleEnd);
      } catch {
        cleanup();
        cameraBusyRef.current = false;
        onFinished?.();
        return false;
      }

      try {
        map.easeTo({
          ...options,
          essential: options.essential ?? true,
        });
      } catch {
        cleanup();
        cameraBusyRef.current = false;
        onFinished?.();
        return false;
      }

      if (typeof map.isMoving === "function" && !map.isMoving()) {
        handleEnd();
      }

      return true;
    },
    [destroyedRef, stopActiveTransition],
  );

  const panToLocation = useCallback(
    (
      location: LocationMarker,
      options: {
        minZoom?: number;
        targetZoom?: number;
        padding?: mapboxgl.PaddingOptions;
        duration?: number;
        onComplete?: () => void;
      } = {},
    ) => {
      if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) return false;

      const map = mapRef.current;
      if (!map || destroyedRef.current) return false;

      const currentZoom = typeof map.getZoom === "function" ? map.getZoom() : 0;
      const minZoom = options.minZoom ?? 14.5;
      const targetZoom = options.targetZoom ?? Math.max(currentZoom, minZoom);
      return performCameraTransition(
        {
          center: [location.lng!, location.lat!],
          zoom: targetZoom,
          padding: options.padding,
          bearing: map.getBearing?.(),
          pitch: map.getPitch?.(),
          duration: options.duration ?? 450,
        },
        options.onComplete,
      );
    },
    [destroyedRef, performCameraTransition],
  );

  const handleResetNorth = useCallback(() => {
    const map = mapRef.current;
    if (!map || destroyedRef.current) return;
    if (typeof map.getBearing !== "function") return;
    const bearing = map.getBearing();
    if (!Number.isFinite(bearing)) return;
    if (Math.abs(bearing) < 0.05) return;

    const center = map.getCenter?.();
    if (!center || !isFiniteCoord(center.lng) || !isFiniteCoord(center.lat)) {
      return;
    }

    const options: EaseOptions & { center: [number, number] } = {
      center: [center.lng, center.lat],
      bearing: 0,
      duration: 400,
    };
    const pitch = typeof map.getPitch === "function" ? map.getPitch() : undefined;
    if (typeof pitch === "number" && Number.isFinite(pitch)) {
      options.pitch = pitch;
    }
    const zoom = typeof map.getZoom === "function" ? map.getZoom() : undefined;
    if (typeof zoom === "number" && Number.isFinite(zoom)) {
      options.zoom = zoom;
    }
    const mapWithPadding = map as MapboxMap & { getPadding?: () => mapboxgl.PaddingOptions };
    const padding = typeof mapWithPadding.getPadding === "function" ? mapWithPadding.getPadding() : undefined;
    if (padding) {
      options.padding = padding;
    }

    const success = performCameraTransition(options);
    if (success) {
      onSuppressNextViewportFetch?.();
    }
  }, [destroyedRef, onSuppressNextViewportFetch, performCameraTransition]);

  const handleLocateUser = useCallback(() => {
    if (destroyedRef.current) return;
    if (typeof navigator === "undefined" || !("geolocation" in navigator) || !navigator.geolocation) {
      clearUserLocation();
      console.info("Geolocation not supported.");
      return;
    }
    if (isLocating) return;

    setIsLocating(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (destroyedRef.current) return;
        setIsLocating(false);

        const { latitude, longitude } = position.coords ?? {};
        if (!isFiniteCoord(longitude) || !isFiniteCoord(latitude)) {
          clearUserLocation();
          console.info("Could not determine your position.");
          return;
        }

        setUserLocation(longitude, latitude, position.coords?.accuracy ?? null);

        const map = mapRef.current;
        if (!map) return;

        const currentZoom = typeof map.getZoom === "function" ? map.getZoom() : MY_LOCATION_ZOOM;
        const targetZoom = Math.max(Number.isFinite(currentZoom) ? currentZoom : MY_LOCATION_ZOOM, MY_LOCATION_ZOOM);

        const options: EaseOptions & { center: [number, number] } = {
          center: [longitude, latitude],
          zoom: targetZoom,
          duration: 500,
        };
        const pitch = typeof map.getPitch === "function" ? map.getPitch() : undefined;
        if (typeof pitch === "number" && Number.isFinite(pitch)) {
          options.pitch = pitch;
        }
        const bearing = typeof map.getBearing === "function" ? map.getBearing() : undefined;
        if (typeof bearing === "number" && Number.isFinite(bearing)) {
          options.bearing = bearing;
        }
        const mapWithPadding = map as MapboxMap & { getPadding?: () => mapboxgl.PaddingOptions };
        const padding = typeof mapWithPadding.getPadding === "function" ? mapWithPadding.getPadding() : undefined;
        if (padding) {
          options.padding = padding;
        }

        const success = performCameraTransition(options);
        if (success) {
          onSuppressNextViewportFetch?.();
        }
      },
      (error) => {
        if (destroyedRef.current) return;
        setIsLocating(false);
        clearUserLocation();
        let message = "Could not determine your position.";
        switch (error.code) {
          case error.PERMISSION_DENIED:
            message = "Location access denied.";
            break;
          case error.POSITION_UNAVAILABLE:
            message = "Location unavailable.";
            break;
          case error.TIMEOUT:
            message = "Location request timed out.";
            break;
          default:
            break;
        }
        console.info(message);
      },
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 0,
      },
    );
  }, [clearUserLocation, destroyedRef, isLocating, onSuppressNextViewportFetch, performCameraTransition, setUserLocation]);

  const handleMarkerSelect = useCallback(
    (id: string) => {
      if (destroyedRef.current) return;
      const location = findLocationById(id);
      if (!location) {
        console.warn("MapView: location not found for id", id);
        return;
      }
      if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
        return;
      }
      onHighlight?.(String(location.id));
      if (!centerOnSelect) {
        switchPopupToLocation(location);
        return;
      }
      hidePopup();
      const success = panToLocation(location, {
        minZoom: 15,
        duration: 420,
        onComplete: () => {
          switchPopupToLocation(location);
        },
      });
      if (!success) {
        switchPopupToLocation(location);
      }
    },
    [centerOnSelect, destroyedRef, findLocationById, hidePopup, onHighlight, panToLocation, switchPopupToLocation],
  );

  const handleClusterFocus = useCallback(
    (center: LngLatLike, zoom: number) => {
      const map = mapRef.current;
      if (!map || destroyedRef.current) return;
      // Suppress viewport fetch when expanding cluster to prevent unnecessary API calls
      onSuppressNextViewportFetch?.();
      const currentZoom = typeof map.getZoom === "function" ? map.getZoom() : 0;
      const targetZoom = Math.max(currentZoom, zoom ?? currentZoom);
      performCameraTransition(
        {
          center: center as [number, number],
          zoom: targetZoom,
          duration: 450,
        },
        undefined,
      );
    },
    [destroyedRef, onSuppressNextViewportFetch, performCameraTransition],
  );

  const startFocusTransition = useCallback(
    (focusKey: string, location: LocationMarker) => {
      const map = mapRef.current;
      if (!map || destroyedRef.current) return false;
      if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
        return false;
      }
      if (!centerOnSelect) {
        if (focusPendingRef.current) {
          focusPendingRef.current.cancel();
          focusPendingRef.current = null;
        }
        hidePopup();
        lastFocusRef.current = focusKey;
        pendingFocusDataRef.current = null;
        switchPopupToLocation(location);
        onHighlight?.(String(location.id));
        onFocusConsumed?.();
        return true;
      }
      if (!isMapFullyLoaded(map)) {
        return false;
      }

      hidePopup();
      lastFocusRef.current = focusKey;

      const paddingData = computeFocusPadding();
      const padding = {
        top: paddingData.top,
        bottom: paddingData.bottom,
        left: 0,
        right: 0,
      };

      if (focusPendingRef.current) {
        focusPendingRef.current.cancel();
      }

      let cancelled = false;
      const cancel = () => {
        if (cancelled) return;
        cancelled = true;
        focusPendingRef.current = null;
      };

      focusPendingRef.current = { id: focusKey, cancel };

      const currentZoom = typeof map.getZoom === "function" ? map.getZoom() : 0;
      const targetZoom = Math.max(currentZoom, 15);

      const success = performCameraTransition(
        {
          center: [location.lng!, location.lat!],
          zoom: targetZoom,
          padding,
          bearing: map.getBearing?.(),
          pitch: map.getPitch?.(),
          duration: cameraBusyRef.current ? 240 : 480,
        },
        () => {
          if (cancelled) return;
          focusPendingRef.current = null;
          pendingFocusDataRef.current = null;
          switchPopupToLocation(location);
          onHighlight?.(String(location.id));
          onFocusConsumed?.();
        },
      );

      if (!success) {
        cancel();
        switchPopupToLocation(location);
        onHighlight?.(String(location.id));
        onFocusConsumed?.();
      }

      return success;
    },
    [centerOnSelect, computeFocusPadding, destroyedRef, hidePopup, isMapFullyLoaded, onFocusConsumed, onHighlight, performCameraTransition, switchPopupToLocation],
  );

  const applyPendingFocus = useCallback(() => {
    const pending = pendingFocusDataRef.current;
    if (!pending) return;
    if (!isFiniteCoord(pending.location.lng) || !isFiniteCoord(pending.location.lat)) {
      console.warn("Skipping focus: invalid coordinates", pending);
      pendingFocusDataRef.current = null;
      onFocusConsumed?.();
      return;
    }
    if (startFocusTransition(pending.id, pending.location)) {
      pendingFocusDataRef.current = null;
    }
  }, [onFocusConsumed, startFocusTransition]);

  const applyPendingFocusRef = useRef(applyPendingFocus);
  useEffect(() => {
    applyPendingFocusRef.current = applyPendingFocus;
  }, [applyPendingFocus]);

  const stopActiveTransitionRef = useRef(stopActiveTransition);
  useEffect(() => {
    stopActiveTransitionRef.current = stopActiveTransition;
  }, [stopActiveTransition]);

  const hidePopupRef = useRef(hidePopup);
  useEffect(() => {
    hidePopupRef.current = hidePopup;
  }, [hidePopup]);

  // Init Map slechts één keer
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapRef.current) return; // guard against StrictMode double-invoke

    destroyedRef.current = false;

    // Use initial center from hook (starts with Rotterdam fallback, may update if geolocation resolves)
    const initialCenter = initialCenterResult.initialCenter;
    const initialZoom = initialCenterResult.initialZoom;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: CONFIG.MAPBOX_STYLE,
      center: [initialCenter.lng, initialCenter.lat],
      zoom: initialZoom,
      attributionControl: false,
    });

    attachCategoryIconFallback(map);
    const primeIcons = () => {
      void ensureCategoryIcons(map);
    };
    map.once("style.load", primeIcons as any);

    mapRef.current = map;
    mapEventCleanupRef.current = [];

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");

    const handleMapClick = (e: mapboxgl.MapMouseEvent) => {
      if (destroyedRef.current) return;
      const handler = onMapClickRef.current;
      if (!handler) return;
      try {
        const feats = map.queryRenderedFeatures(e.point) as any[];
        const interactiveHit =
          Array.isArray(feats) &&
          feats.some(
            (f) =>
              f?.layer?.id === "tda-unclustered-point" ||
              f?.layer?.id === "tda-clusters" ||
              f?.layer?.id === "tda-cluster-count",
          );
        if (interactiveHit) return;
      } catch {
        /* ignore */
      }
      handler();
    };
    map.on("click", handleMapClick);
    mapEventCleanupRef.current.push(() => {
      try {
        map.off("click", handleMapClick);
      } catch {
        /* ignore */
      }
    });

    mapEventCleanupRef.current.push(() => {
      try {
        map.off("style.load", primeIcons as any);
      } catch {
        /* ignore */
      }
    });

    const handleLoad = async () => {
      if (destroyedRef.current) return;
      
      // Register cluster sprites first (async operation)
      // This must complete before ensureBaseLayers runs, which creates layers that reference these sprites
      try {
        await registerClusterSprites(map);
      } catch (err) {
        console.error("[MapView] Failed to register cluster sprites:", err);
        // Don't throw - markers should work even if cluster sprites fail
      }
      
      // Create base marker layers (synchronous, sprites should be ready now)
      ensureBaseLayers(map);
      
      setMapReady(true);
      applyPendingFocusRef.current?.();
    };
    map.on("load", handleLoad);
    mapEventCleanupRef.current.push(() => {
      try {
        map.off("load", handleLoad);
      } catch {
        /* ignore */
      }
    });

    return () => {
      destroyedRef.current = true;
      stopActiveTransitionRef.current?.();
      mapEventCleanupRef.current.forEach((fn) => fn());
      mapEventCleanupRef.current = [];
      if (focusPendingRef.current) {
        focusPendingRef.current.cancel();
        focusPendingRef.current = null;
      }
      pendingFocusDataRef.current = null;
      hidePopupRef.current?.();
      const mapInstance = mapRef.current;
      if (mapInstance) {
        try {
          mapInstance.stop();
        } catch {
          /* ignore */
        }
        removeUserLocationLayers();
        try {
          mapInstance.remove();
        } catch {
          /* ignore */
        }
      }
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  // Handle initial center resolution and camera cache
  useEffect(() => {
    if (destroyedRef.current) return;
    
    // Clear camera cache proactively when geolocation is being used or resolved
    // (status === "resolving" means we're requesting geolocation, source === "geolocation" means it succeeded)
    if (initialCenterResult.source === "geolocation" || initialCenterResult.status === "resolving") {
      clearCamera();
    }
    
    if (initialCenterResult.status === "resolved" && !initialCenterAppliedRef.current) {
      initialCenterAppliedRef.current = true;
    }
  }, [initialCenterResult.status, initialCenterResult.source]);

  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    const map = mapRef.current;
    if (!map) return;
    
    // Wait until we know what the initial center is
    if (initialCenterResult.status !== "resolved") return;
    
    // If geolocation is used, skip camera restore entirely
    if (initialCenterResult.source === "geolocation") {
      return;
    }
    
    // If initial view already applied, don't override it
    if (initialViewSettledRef.current) {
      return;
    }
    
    const isFocusActive = Boolean(focusId);
    restoreCamera(map, isFocusActive);
  }, [mapReady, focusId, initialCenterResult.status, initialCenterResult.source]);

  const applyInitialView = useCallback(
    (target: { center: [number, number]; zoom: number }) => {
      if (destroyedRef.current || initialViewSettledRef.current) return;
      if (cameraBusyRef.current) return;

      const map = mapRef.current;
      if (!map) return;

      if (import.meta.env.DEV) {
        console.debug("[InitialMapCameraApplied]", {
          center: target.center,
          zoom: target.zoom,
          source: initialCenterResult.source,
        });
      }

      const success = performCameraTransition(
        {
          center: target.center,
          zoom: target.zoom,
          duration: 400,
        },
        () => {
          initialViewSettledRef.current = true;
        }
      );

      if (success) {
        onSuppressNextViewportFetch?.();
        // Mark as settled even if transition completes later
        // (the callback will also set it, but this ensures it's set immediately)
        initialViewSettledRef.current = true;
      } else {
        // Transition failed, mark as settled anyway to avoid retrying
        initialViewSettledRef.current = true;
      }
    },
    [destroyedRef, onSuppressNextViewportFetch, performCameraTransition, initialCenterResult.source]
  );

  // Apply unclustered marker visibility heuristic once on initial load
  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    if (initialViewSettledRef.current) return;
    if (initialCenterResult.status !== "resolved") return;
    if (locations.length === 0) return; // Wait for locations to be loaded
    
    // Only check cameraBusy if we've already attempted initial view
    if (initialViewAttemptedRef.current && cameraBusyRef.current) return;
    initialViewAttemptedRef.current = true;

    const map = mapRef.current;
    if (!map) return;

    // Check if marker layer is ready (source exists and has data)
    const source = map.getSource(MarkerLayerIds.SRC_ID);
    if (!source) return;

    const mobile = isMobile();
    const initialCenter: [number, number] = [
      initialCenterResult.initialCenter.lng,
      initialCenterResult.initialCenter.lat,
    ];
    const fallbackCenter: [number, number] = [
      CONFIG.MAP_DEFAULT.lng,
      CONFIG.MAP_DEFAULT.lat,
    ];
    const fallbackZoom = CONFIG.MAP_DEFAULT.zoom;

    const target = computeInitialUnclusteredView({
      map,
      isMobile: mobile,
      initialCenter,
      fallbackCenter,
      fallbackZoom,
    });

    if (!target) {
      // No target computed - keep current view
      initialViewSettledRef.current = true;
      return;
    }

    // If it's a cluster, try to get expansion zoom
    if (typeof target.clusterId === "number") {
      const geojsonSource = source as any;
      if (typeof geojsonSource.getClusterExpansionZoom === "function") {
        geojsonSource.getClusterExpansionZoom(
          target.clusterId,
          (err: unknown, expansionZoom: number) => {
            if (destroyedRef.current || initialViewSettledRef.current) return;
            if (err || !Number.isFinite(expansionZoom)) {
              // Use the target zoom we already computed
              applyInitialView(target);
              return;
            }

            // Cap zoom at cluster max zoom
            const clusterMaxZoom = mobile ? CLUSTER_CONFIG.MOBILE_MAX_ZOOM : CLUSTER_CONFIG.MAX_ZOOM;
            const finalZoom = Math.min(expansionZoom, clusterMaxZoom);

            applyInitialView({
              center: target.center,
              zoom: finalZoom,
            });
          }
        );
        return;
      }
    }

    // Not a cluster or expansion zoom not available - apply directly
    applyInitialView(target);
  }, [mapReady, locations.length, initialCenterResult.status, initialCenterResult.initialCenter, initialCenterResult.initialZoom, applyInitialView]);

  useEffect(() => {
    if (!focusId) {
      lastFocusRef.current = null;
      pendingFocusDataRef.current = null;
      if (focusPendingRef.current) {
        focusPendingRef.current.cancel();
        focusPendingRef.current = null;
      }
      return;
    }

    const location = findLocationById(focusId);
    if (!location) {
      console.warn("MapView: cannot focus, location not found for id", focusId);
      onFocusConsumed?.();
      return;
    }
    if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
      console.warn("Skipping focus: invalid coordinates", { id: focusId, location });
      onFocusConsumed?.();
      return;
    }

    if (startFocusTransition(focusId, location)) {
      pendingFocusDataRef.current = null;
      return;
    }

    pendingFocusDataRef.current = { id: focusId, location };

    const map = mapRef.current;
    if (!map) {
      return;
    }

    const handleLoad = () => {
      if (destroyedRef.current) return;
      if (!pendingFocusDataRef.current || pendingFocusDataRef.current.id !== focusId) return;
      if (startFocusTransition(focusId, pendingFocusDataRef.current.location)) {
        pendingFocusDataRef.current = null;
      }
    };

    try {
      map.once("load", handleLoad);
    } catch {
      map.on("load", handleLoad);
    }

    const cancelLoad = () => {
      try {
        map.off("load", handleLoad);
      } catch {
        /* ignore */
      }
    };

    if (focusPendingRef.current) {
      focusPendingRef.current.cancel();
    }
    focusPendingRef.current = {
      id: focusId,
      cancel: () => {
        cancelLoad();
        pendingFocusDataRef.current = null;
      },
    };

    return () => {
      cancelLoad();
    };
  }, [destroyedRef, findLocationById, focusId, onFocusConsumed, startFocusTransition]);

  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;

    if (detailId) {
      if (focusPendingRef.current) {
        focusPendingRef.current.cancel();
        focusPendingRef.current = null;
      }
      hidePopup();
      return;
    }

    if (!highlightedId) {
      hidePopup();
      return;
    }

    const location = findLocationById(highlightedId);
    if (!location) {
      hidePopup();
      return;
    }
    if (typeof location.lng !== "number" || typeof location.lat !== "number") {
      hidePopup();
      return;
    }

    const alreadyVisible = popup.isVisible() && popup.currentId() === String(location.id);
    if (!alreadyVisible) {
      switchPopupToLocation(location);
    }
    popup.updateAnchor();
  }, [destroyedRef, detailId, highlightedId, locations, mapReady, findLocationById, hidePopup, popup, switchPopupToLocation]);

  useEffect(() => {
    return () => {
      hidePopup();
      if (viewportDebounceRef.current !== null) {
        window.clearTimeout(viewportDebounceRef.current);
        viewportDebounceRef.current = null;
      }
      const map = mapRef.current;
      if (map) {
        storeCamera(map);
      }
    };
  }, [hidePopup]);

  return (
    <div
      className={cn(
        "relative h-full w-full",
        interactionDisabled && "pointer-events-none"
      )}
    >
      <div
        ref={mapContainerRef}
        className="relative h-full w-full overflow-hidden"
      />
      {mapReady && mapRef.current && (
        <MapControls
          onResetNorth={handleResetNorth}
          onLocateUser={handleLocateUser}
          locating={isLocating}
          disabled={interactionDisabled}
        />
      )}
      {mapReady && mapRef.current && (
        <MarkerLayer
          map={mapRef.current}
          locations={locations}
          selectedId={highlightedId}
          onSelect={handleMarkerSelect}
          onClusterFocus={handleClusterFocus}
        />
      )}
    </div>
  );
}

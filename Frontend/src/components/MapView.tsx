
// src/components/MapView.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import mapboxgl, { Map as MapboxMap, type LngLatLike } from "mapbox-gl";
import { useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { createRoot, type Root } from "react-dom/client";

import { restoreCamera, storeCamera } from "@/components/mapCameraCache";
import { MARKER_POINT_OUTER_RADIUS } from "@/components/markerLayerUtils";
import PreviewTooltip from "@/components/PreviewTooltip";
import { cn } from "@/lib/ui/cn";
import MarkerLayer from "./MarkerLayer";

// Zorg dat je VITE_MAPBOX_TOKEN in .env staat
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || "";

type Props = {
  locations: LocationMarker[];
  highlightedId: string | null;
  detailId: string | null;
  onHighlight?: (id: string | null) => void;
  onOpenDetail?: (id: string) => void;
  onMapClick?: () => void;
  onViewportChange?: (bbox: string | null) => void;
  interactionDisabled?: boolean;
  focusId?: string | null;
  onFocusConsumed?: () => void;
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
const FOCUS_BIAS_RATIO = 0.15;
type EaseOptions = Parameters<MapboxMap["easeTo"]>[0];

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
      defer(() => {
        try {
          current.root.render(null);
        } catch {
          /* ignore */
        }
      });
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
  highlightedId,
  detailId,
  onHighlight,
  onOpenDetail,
  onMapClick,
  onViewportChange,
  interactionDisabled = false,
  focusId,
  onFocusConsumed,
}: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const lastBboxRef = useRef<string | null>(null);
  const lastFocusRef = useRef<string | null>(null);
  const focusPendingRef = useRef<{ id: string; cancel: () => void } | null>(null);
  const allLocationsRef = useRef<LocationMarker[]>(locations);
  const destroyedRef = useRef(false);
  const pendingFocusDataRef = useRef<{ id: string; location: LocationMarker } | null>(null);
  const mapEventCleanupRef = useRef<(() => void)[]>([]);
  const cameraBusyRef = useRef(false);
  const transitionCleanupRef = useRef<(() => void) | null>(null);
  const viewportDebounceRef = useRef<number | null>(null);
  const popup = usePopupController(mapRef, mapReady, destroyedRef);
  const onMapClickRef = useRef(onMapClick);

  useEffect(() => {
    onMapClickRef.current = onMapClick;
  }, [onMapClick]);

  const findLocationById = useCallback((id: string | number | null | undefined) => {
    if (id == null) return null;
    return allLocationsRef.current.find((loc) => String(loc.id) === String(id)) ?? null;
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
    if (!onViewportChange) return;
    const map = mapRef.current;
    if (!map) return;

    const emit = (bbox: string | null) => {
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
        const bounds = map.getBounds?.();
        if (!bounds) {
          emit(null);
          return;
        }

        const zoom = map.getZoom?.();
        const sw = bounds.getSouthWest?.();
        const ne = bounds.getNorthEast?.();
        if (!sw || !ne || typeof sw.lng !== "number" || typeof sw.lat !== "number" || typeof ne.lng !== "number" || typeof ne.lat !== "number") {
          emit(null);
          return;
        }

        const isZoomedOut = typeof zoom === "number" && (zoom <= 2 || (ne.lng - sw.lng) > 180 || (ne.lat - sw.lat) > 90);
        const nextBbox = isZoomedOut ? null : `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`;
        emit(nextBbox);
      } catch {
        emit(null);
      }
    };

    handle();
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
  }, [destroyedRef, mapReady, onViewportChange]);

  useEffect(() => {
    allLocationsRef.current = locations;
  }, [locations]);

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

  const handleMarkerSelect = useCallback(
    (id: string) => {
      if (destroyedRef.current) return;
      const location = findLocationById(id);
      if (!location || !isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
        return;
      }
      onHighlight?.(String(location.id));
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
    [destroyedRef, findLocationById, hidePopup, onHighlight, panToLocation, switchPopupToLocation],
  );

  const handleClusterFocus = useCallback(
    (center: LngLatLike, zoom: number) => {
      const map = mapRef.current;
      if (!map || destroyedRef.current) return;
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
    [destroyedRef, performCameraTransition],
  );

  const startFocusTransition = useCallback(
    (focusKey: string, location: LocationMarker) => {
      const map = mapRef.current;
      if (!map || destroyedRef.current) return false;
      if (!isFiniteCoord(location.lng) || !isFiniteCoord(location.lat)) {
        return false;
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
    [computeFocusPadding, destroyedRef, hidePopup, isMapFullyLoaded, onFocusConsumed, onHighlight, performCameraTransition, switchPopupToLocation],
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

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: import.meta.env.VITE_MAPBOX_STYLE || "mapbox://styles/mapbox/streets-v12",
      center: [4.4777, 51.9244], // Rotterdam default
      zoom: 11,
      attributionControl: false,
    });

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
        const hiHit = Array.isArray(feats) && feats.some((f) => f?.layer?.id === "tda-highlight");
        if (hiHit) {
          handler();
          return;
        }
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

    const handleLoad = () => {
      if (destroyedRef.current) return;
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

  useEffect(() => {
    if (!mapReady || destroyedRef.current) return;
    const map = mapRef.current;
    if (!map) return;
    const isFocusActive = Boolean(focusId);
    restoreCamera(map, isFocusActive);
  }, [mapReady, focusId]);

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
    if (!location || typeof location.lng !== "number" || typeof location.lat !== "number") {
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
        className="relative h-full w-full overflow-hidden rounded-lg shadow-md"
      />
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

import type { LocationMarker } from "@/api/fetchLocations";
import {
  attachCategoryIconFallback,
  DEFAULT_ICON_ID,
  ensureCategoryIcons,
  getCategoryIconIdForLocation,
  normalizeCategoryKey,
} from "@/lib/map/categoryIcons";
import { CLUSTER_CONFIG } from "@/lib/config";
import { isMobile } from "@/lib/utils";
import type { Map as MapboxMap } from "mapbox-gl";

const SRC_ID = "tda-places";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_HALO = "tda-point-halo";
const L_POINT = "tda-unclustered-point";
const L_POINT_FALLBACK = "tda-unclustered-circle-fallback";

export const MARKER_POINT_RADIUS = 6;
export const MARKER_POINT_STROKE_WIDTH = 2;
export const MARKER_POINT_OUTER_RADIUS = MARKER_POINT_RADIUS + MARKER_POINT_STROKE_WIDTH;
export const MARKER_POINT_DIAMETER = MARKER_POINT_OUTER_RADIUS * 2;

// Track cluster config per map instance to detect changes
type ClusterConfig = { clusterMaxZoom: number; clusterRadius: number };
const mapClusterConfigs = new WeakMap<MapboxMap, ClusterConfig>();

/**
 * Calculate cluster configuration based on device type
 */
function getClusterConfig(): ClusterConfig {
  const mobile = isMobile();
  return {
    clusterMaxZoom: mobile ? CLUSTER_CONFIG.MOBILE_MAX_ZOOM : CLUSTER_CONFIG.MAX_ZOOM,
    clusterRadius: mobile
      ? CLUSTER_CONFIG.RADIUS * CLUSTER_CONFIG.MOBILE_RADIUS_MULTIPLIER
      : CLUSTER_CONFIG.RADIUS,
  };
}

export function buildMarkerGeoJSON(locations: LocationMarker[]) {
  return {
    type: "FeatureCollection" as const,
    features: locations
      .filter((l) => typeof l.lat === "number" && typeof l.lng === "number")
      .map((l) => ({
        type: "Feature" as const,
        properties: {
          id: String(l.id),
          name: l.name,
          category: l.category ?? "",
          categoryKey: normalizeCategoryKey(l.category_key ?? l.category ?? ""),
          confidence: l.confidence_score ?? null,
          icon: getCategoryIconIdForLocation(l) || DEFAULT_ICON_ID,
        },
        geometry: {
          type: "Point" as const,
          coordinates: [l.lng as number, l.lat as number] as [number, number],
        },
      })),
  };
}

function addLayers(map: MapboxMap, config: ClusterConfig) {
  attachCategoryIconFallback(map);
  void ensureCategoryIcons(map);

  if (!map.getSource(SRC_ID)) {
    map.addSource(SRC_ID, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
      cluster: true,
      clusterMaxZoom: config.clusterMaxZoom,
      clusterRadius: config.clusterRadius,
      promoteId: "id",
    } as any);
  }

  if (!map.getLayer(L_CLUSTER)) {
    map.addLayer({
      id: L_CLUSTER,
      type: "circle",
      source: SRC_ID,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": ["step", ["get", "point_count"], "#88c0ff", 25, "#5599ff", 100, "#2b6fe3"],
        "circle-radius": ["step", ["get", "point_count"], 16, 25, 22, 100, 28],
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 2,
      },
    });
  }

  if (!map.getLayer(L_CLUSTER_COUNT)) {
    map.addLayer({
      id: L_CLUSTER_COUNT,
      type: "symbol",
      source: SRC_ID,
      filter: ["has", "point_count"],
      layout: {
        "text-field": ["get", "point_count_abbreviated"],
        "text-size": 12,
      },
      paint: { "text-color": "#083269" },
    });
  }

  if (!map.getLayer(L_POINT_FALLBACK)) {
    map.addLayer({
      id: L_POINT_FALLBACK,
      type: "circle",
      source: SRC_ID,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-radius": 3,
        "circle-color": "#0ea5e9",
        "circle-opacity": 0.25,
      },
    });
  }

  if (!map.getLayer(L_HALO)) {
    map.addLayer({
      id: L_HALO,
      type: "circle",
      source: SRC_ID,
      filter: ["!", ["has", "point_count"]],
      paint: {
        "circle-color": "#0ea5e9",
        "circle-opacity": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          0.35,
          0,
        ],
        "circle-radius": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          10,
          0,
        ],
      },
    });
  }

  if (!map.getLayer(L_POINT)) {
    map.addLayer({
      id: L_POINT,
      type: "symbol",
      source: SRC_ID,
      filter: ["!", ["has", "point_count"]],
      layout: {
        "icon-image": ["coalesce", ["image", ["get", "icon"]], ["image", DEFAULT_ICON_ID]],
        "icon-size": 1,
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        "icon-keep-upright": true,
      },
      paint: {
        "icon-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 1, 0.82],
      },
    });
  }

  if (map.getLayer(L_HALO) && map.getLayer(L_POINT) && typeof map.moveLayer === "function") {
    try {
      map.moveLayer(L_HALO, L_POINT);
    } catch {
      /* ignore */
    }
  }
}

/**
 * Remove all marker layers in reverse order (dependencies first)
 */
function removeMarkerLayers(map: MapboxMap) {
  // Remove layers in reverse dependency order
  const layersToRemove = [L_POINT, L_HALO, L_POINT_FALLBACK, L_CLUSTER_COUNT, L_CLUSTER];
  for (const layerId of layersToRemove) {
    try {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
    } catch {
      /* ignore */
    }
  }
}

/**
 * Recreate source and layers with new cluster configuration
 */
function recreateSourceWithConfig(map: MapboxMap, config: ClusterConfig) {
  const existingSource = map.getSource(SRC_ID);
  const existingData = existingSource && typeof (existingSource as any).getData === "function"
    ? (existingSource as any).getData()
    : null;

  // Remove layers first
  removeMarkerLayers(map);

  // Remove source
  try {
    if (existingSource) {
      map.removeSource(SRC_ID);
    }
  } catch {
    /* ignore */
  }

  // Add source with new config
  map.addSource(SRC_ID, {
    type: "geojson",
    data: existingData || { type: "FeatureCollection", features: [] },
    cluster: true,
    clusterMaxZoom: config.clusterMaxZoom,
    clusterRadius: config.clusterRadius,
    promoteId: "id",
  } as any);

  // Re-add layers
  addLayers(map, config);
}

export function ensureBaseLayers(map: MapboxMap) {
  if (!map) return;
  const isStyleLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
  if (!isStyleLoaded) {
    const handler = () => {
      const loaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
      if (!loaded) return;
      try {
        map.off("styledata", handler as any);
      } catch {
        /* ignore */
      }
      ensureBaseLayers(map);
    };
    try {
      map.once("styledata", handler as any);
    } catch {
      map.on("styledata", handler as any);
    }
    return;
  }

  const currentConfig = getClusterConfig();
  const existingSource = map.getSource(SRC_ID);
  const storedConfig = mapClusterConfigs.get(map);

  // Check if source exists and config has changed
  if (existingSource && storedConfig) {
    const configChanged =
      storedConfig.clusterMaxZoom !== currentConfig.clusterMaxZoom ||
      storedConfig.clusterRadius !== currentConfig.clusterRadius;

    if (configChanged) {
      // Recreate source and layers with new config
      recreateSourceWithConfig(map, currentConfig);
      mapClusterConfigs.set(map, currentConfig);
      return;
    }
  }

  // Source doesn't exist or config matches - proceed normally
  if (!existingSource) {
    addLayers(map, currentConfig);
    mapClusterConfigs.set(map, currentConfig);
  } else {
    // Source exists and config matches - just ensure layers exist
    addLayers(map, currentConfig);
    // Update stored config in case it wasn't set before
    if (!storedConfig) {
      mapClusterConfigs.set(map, currentConfig);
    }
  }
}

export const MarkerLayerIds = {
  SRC_ID,
  L_CLUSTER,
  L_CLUSTER_COUNT,
  L_HALO,
  L_POINT_FALLBACK,
  L_POINT,
} as const;

export function ensureIconIdsForFeatures(map: MapboxMap, _features: any[]): void {
  if (!map) return;
  void ensureCategoryIcons(map);
}


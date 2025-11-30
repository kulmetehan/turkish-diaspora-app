import type { LocationMarker } from "@/api/fetchLocations";
import { CLUSTER_CONFIG } from "@/lib/config";
import {
  attachCategoryIconFallback,
  DEFAULT_ICON_ID,
  ensureCategoryIcons,
  getCategoryIconIdForLocation,
  normalizeCategoryKey,
  renderSvgToCanvas,
  roundDPR,
  toBitmap,
} from "@/lib/map/categoryIcons";
import { isMobile } from "@/lib/utils";
import type { Map as MapboxMap } from "mapbox-gl";

const SRC_ID = "tda-places";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_HALO = "tda-point-halo";
const L_POINT = "tda-unclustered-point";
const L_POINT_FALLBACK = "tda-unclustered-circle-fallback";

// F4-S2: Updated for 32px Snap-style markers
export const MARKER_POINT_RADIUS = 16; // Half of 32px icon size
export const MARKER_POINT_STROKE_WIDTH = 2;
export const MARKER_POINT_OUTER_RADIUS = MARKER_POINT_RADIUS + MARKER_POINT_STROKE_WIDTH; // 18px
export const MARKER_POINT_DIAMETER = MARKER_POINT_OUTER_RADIUS * 2;

// US-P2 / EPIC-7: Turkspot cluster styling constants
// Premium cluster design: semi-transparent red background with white text (borderless for clean look)
// Cluster chip colors – SVG uses rgba for transparency, Mapbox layer uses hex
const CLUSTER_BG_RGBA = "rgba(225, 6, 0, 0.3)"; // Semi-transparent Ferrari red background (30% opacity)
const CLUSTER_BORDER_HEX = "#e10600"; // Ferrari-style red (kept for text halo, but no border on sprite)
const CLUSTER_TEXT_HEX = "#ffffff";   // White text for contrast
const CLUSTER_RADIUS = 12; // Rounded-square border radius (pill-square shape, increased from 8px)
const CLUSTER_FONT_WEIGHT = 600; // semibold
const CLUSTER_FONT_SIZE_BASE = 12;

// US-P2 / EPIC-7: Generate SVG sprite for cluster rounded-square backgrounds
// Creates semi-transparent red rounded rectangle with subtle shadow for depth (borderless for clean look)
// Size parameter controls the dimensions (will be used for small/medium/large variants)
function generateClusterSprite(size: number): string {
  const radius = CLUSTER_RADIUS;
  const bgColor = CLUSTER_BG_RGBA; // Semi-transparent red background

  // Generate unique filter ID to avoid conflicts if multiple sprites are generated
  const filterId = `cluster-shadow-${size}`;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <!-- Subtle shadow/glow filter for depth -->
    <filter id="${filterId}" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
      <feOffset dx="0" dy="1" result="offsetblur"/>
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.3"/>
      </feComponentTransfer>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <!-- Semi-transparent red rounded rectangle with shadow (no border for clean look) -->
  <rect x="0" y="0" width="${size}" height="${size}" rx="${radius}" ry="${radius}" 
        fill="${bgColor}" stroke="none" filter="url(#${filterId})" />
</svg>`;
}

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

// US-P2 / EPIC-7: Register cluster sprite images with Mapbox map
// Generates and registers 3 sprite variants (small/medium/large) for rounded-square cluster backgrounds
// Performance: Pre-generating 3 sprites is more efficient than dynamic generation per cluster
// Premium design: semi-transparent red background, red border, white text, 12px border radius
// TODO(tda-clusters-animations): Future enhancements for hover/click interactions
// - Consider adding a brief "pulse" animation when clusters split on zoom
// - Consider a subtle opacity/scale transition when cluster markers mount/unmount
// - Note: Mapbox symbol layers don't support CSS hover states; animations would need to be
//   handled via Mapbox feature-state or by switching to HTML markers if interactive animations are needed
// This is called separately on map load (in MapView.tsx) to keep layer creation synchronous
export async function registerClusterSprites(map: MapboxMap): Promise<void> {
  if (!map || typeof map.addImage !== "function") return;

  const dpr = roundDPR(typeof window !== "undefined" ? window.devicePixelRatio : 1);

  // Cluster sprite sizes: small (32px), medium (40px), large (48px)
  // Updated sizes for premium visual design with better proportions
  // Small: up to 24 points, Medium: 25-99 points, Large: 100+ points
  const spriteConfigs = [
    { id: "tda-cluster-small", size: 32 },   // For point_count ≤ 24
    { id: "tda-cluster-medium", size: 40 },  // For point_count 25-99
    { id: "tda-cluster-large", size: 48 },   // For point_count 100+ (increased visual presence)
  ];

  for (const config of spriteConfigs) {
    // Skip if already registered
    if (map.hasImage?.(config.id)) continue;

    try {
      // Generate SVG sprite using Turkspot rounded-square design
      const svg = generateClusterSprite(config.size);
      // Convert to canvas and bitmap (handles device pixel ratio for crisp rendering)
      const canvas = await renderSvgToCanvas(svg, config.size, dpr);
      const bitmap = await toBitmap(canvas);
      // Register with map (reused across all clusters of the same size)
      map.addImage(config.id, bitmap as any, { pixelRatio: dpr });
    } catch (error) {
      console.warn(`Failed to register cluster sprite ${config.id}:`, error);
    }
  }
}

function addLayers(map: MapboxMap, config: ClusterConfig) {
  attachCategoryIconFallback(map);
  void ensureCategoryIcons(map);

  // Note: Cluster sprites are registered separately on map load (see MapView.tsx)
  // This keeps layer creation synchronous and deterministic

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

  // US-P2 / EPIC-7: Replace circle cluster with rounded-square symbol cluster
  // Remove old circle layer if it exists (legacy)
  if (map.getLayer(L_CLUSTER)) {
    try {
      map.removeLayer(L_CLUSTER);
    } catch {
      /* ignore if already removed */
    }
  }

  // US-P2 / EPIC-7: Add symbol layer with rounded-square icon + text overlay
  // Replaces old circle cluster layer with Turkspot-styled rounded-square badges
  // Uses icon-image for background sprite and text-field for count label overlay
  // Layer ID remains L_CLUSTER for backward compatibility with click handlers
  if (!map.getLayer(L_CLUSTER)) {
    map.addLayer({
      id: L_CLUSTER,
      type: "symbol",
      source: SRC_ID,
      filter: ["has", "point_count"],
      layout: {
        // Select sprite based on point_count: small (≤24), medium (25-99), large (100+)
        // Dynamic sprite selection provides appropriate size for cluster density
        "icon-image": [
          "step",
          ["get", "point_count"],
          "tda-cluster-small",
          25,
          "tda-cluster-medium",
          100,
          "tda-cluster-large",
        ],
        "icon-size": 1.0, // Use sprite at native size (no scaling)
        "icon-anchor": "center",
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        // Overlay count text on top of icon (centered)
        "text-field": ["get", "point_count_abbreviated"],
        // Scale text size with cluster size for optimal readability
        // Text scales: 12px (small), 14px (medium), 16px (large)
        "text-size": [
          "step",
          ["get", "point_count"],
          CLUSTER_FONT_SIZE_BASE, // 12px for small clusters (≤24)
          25,
          14, // 14px for medium clusters (25-99)
          100,
          16, // 16px for large clusters (100+)
        ],
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-offset": [0, 0], // Center text on icon
        "text-optional": false, // Always show text (count is essential)
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": CLUSTER_TEXT_HEX, // White text on semi-transparent red background
        // Subtle text halo for better readability across different map backgrounds
        // Use semi-transparent red halo to match the cluster background
        "text-halo-color": CLUSTER_BORDER_HEX,
        "text-halo-width": 1.5,
        "text-halo-blur": 0.5,
      },
    });
  }

  // Remove old L_CLUSTER_COUNT layer if it exists (merged into L_CLUSTER)
  if (map.getLayer(L_CLUSTER_COUNT)) {
    try {
      map.removeLayer(L_CLUSTER_COUNT);
    } catch {
      /* ignore if already removed */
    }
  }

  // Layer order (bottom to top):
  // 1. L_POINT_FALLBACK - subtle circle fallback for unclustered points
  // 2. L_HALO - selection halo ring (rendered below marker icons)
  // 3. L_POINT - unclustered marker icons (symbol layer)
  // 4. L_CLUSTER - cluster chips (symbol layer with white bg + red border)

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
          0.4, // F4-S2: Increased from 0.35 for better visibility
          0,
        ],
        "circle-radius": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          14, // F4-S2: Increased from 10 to match new 32px icon size
          0,
        ],
        "circle-stroke-color": "#FFFFFF", // F4-S2: White stroke for better contrast
        "circle-stroke-width": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          1.5,
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
        // F4-S2: Constant icon-size (feature-state not allowed in layout properties)
        // Selected state is handled via paint properties (opacity) and halo layer
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

  // Ensure L_HALO renders below L_POINT (halo should be behind marker icons)
  if (map.getLayer(L_HALO) && map.getLayer(L_POINT) && typeof map.moveLayer === "function") {
    try {
      map.moveLayer(L_HALO, L_POINT);
    } catch {
      /* ignore */
    }
  }

  // Layer filters ensure no overlap:
  // - L_CLUSTER: ["has", "point_count"] - only clustered points
  // - L_POINT, L_HALO, L_POINT_FALLBACK: ["!", ["has", "point_count"]] - only unclustered points
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

  // Re-add layers (synchronous - sprites should already be registered)
  addLayers(map, config);
}

export function ensureBaseLayers(map: MapboxMap) {
  if (!map) return;
  const isStyleLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
  if (!isStyleLoaded) {
    // Return early if style not loaded - caller should retry after style loads
    // (Typically handled by map.on("load") or map.on("styledata"))
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
  // addLayers() is idempotent (checks if layers exist before adding)
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


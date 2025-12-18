import { fetchCategories, type CategoryOption } from "@/api/fetchLocations";
import { Button } from "@/components/ui/button";
import { getCityDistricts, getDiscoveryCoverage, type CityReadiness, type DiscoveryCoverageCell } from "@/lib/api";
import { CONFIG } from "@/lib/config";
import { initMap } from "@/lib/map/mapbox";
import type { FeatureCollection, Point, Polygon } from "geojson";
import mapboxgl, { Map as MapboxMap, Popup } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";

// Safe date formatter that handles null/undefined values using native Date APIs
function formatDateOrDash(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("nl-NL", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

mapboxgl.accessToken = CONFIG.MAPBOX_TOKEN;

function safeHasLayer(map: MapboxMap | null | undefined, id: string): boolean {
  if (!map) return false;
  // Guard against empty or undefined layer IDs to prevent "IDs can't be empty" errors
  if (!id || typeof id !== "string" || id.trim() === "") return false;
  try {
    return Boolean(map.getLayer(id));
  } catch {
    return false;
  }
}

const COVERAGE_SOURCE_ID = "tda-discovery-coverage";
const COVERAGE_LAYER_ID = "tda-discovery-coverage-layer";
const COVERAGE_OUTLINE_LAYER_ID = "tda-discovery-coverage-outline";
const HEATMAP_SOURCE_ID = "tda-discovery-coverage-heatmap";
const HEATMAP_LAYER_ID = "tda-discovery-coverage-heatmap-layer";

// Cell spacing in meters (approximate, matches discovery_bot logic)
const CELL_SPACING_M = 750; // nearby_radius_m * 0.75 = 1000 * 0.75

// Color scheme
const COLOR_NOT_VISITED = "#9ca3af"; // grey
const COLOR_WITH_INSERTS = "#10b981"; // green
const COLOR_NO_INSERTS = "#f59e0b"; // yellow
const COLOR_HIGH_ERROR = "#ef4444"; // red
const ERROR_THRESHOLD = 0.1; // 10% error rate

function metersToDegrees(meters: number, atLat: number): { lat: number; lng: number } {
  const earthRadiusM = 6371000;
  const latDeg = meters / earthRadiusM * (180 / Math.PI);
  const lngDeg = meters / (earthRadiusM * Math.cos((atLat * Math.PI) / 180)) * (180 / Math.PI);
  return { lat: latDeg, lng: lngDeg };
}

function createCellPolygon(
  latCenter: number,
  lngCenter: number,
  spacingM: number
): Polygon {
  const half = metersToDegrees(spacingM / 2, latCenter);
  return {
    type: "Polygon",
    coordinates: [
      [
        [lngCenter - half.lng, latCenter - half.lat],
        [lngCenter + half.lng, latCenter - half.lat],
        [lngCenter + half.lng, latCenter + half.lat],
        [lngCenter - half.lng, latCenter + half.lat],
        [lngCenter - half.lng, latCenter - half.lat],
      ],
    ],
  };
}

function getCellColorFromVisitCount(visitCount: number): string {
  if (visitCount === 0) return "#9ca3af"; // grey for unvisited
  // Gradient based on visit count
  if (visitCount >= 50) return "#10b981"; // green for high activity
  if (visitCount >= 10) return "#f59e0b"; // yellow for medium
  return "#fbbf24"; // lighter yellow for low
}

// Legacy function for backward compatibility
function getCellColor(cell: { calls: number; inserts: number; error429: number; errorOther: number }): string {
  if (cell.calls === 0) {
    return COLOR_NOT_VISITED;
  }

  const totalErrors = cell.error429 + cell.errorOther;
  const errorRate = cell.calls > 0 ? totalErrors / cell.calls : 0;

  if (errorRate > ERROR_THRESHOLD) {
    return COLOR_HIGH_ERROR;
  }

  if (cell.inserts > 0) {
    return COLOR_WITH_INSERTS;
  }

  return COLOR_NO_INSERTS;
}

interface AdminDiscoveryMapProps {
  selectedCity: string;
  onCityChange: (city: string) => void;
  cities: CityReadiness[];
  citiesLoading: boolean;
  citiesError: string | null;
}

export default function AdminDiscoveryMap({
  selectedCity,
  onCityChange,
  cities,
  citiesLoading,
  citiesError,
}: AdminDiscoveryMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const [showCoverage, setShowCoverage] = useState(false);
  const [gridData, setGridData] = useState<DiscoveryCoverageCell[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [districts, setDistricts] = useState<string[]>([]);
  const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
  const [showGridOverlay, setShowGridOverlay] = useState(true);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = initMap(mapContainerRef.current);
    mapRef.current = map;

    // Default center (fallback if no data)
    const defaultCenter: [number, number] = [4.4777, 51.9225];
    const mapCenter: [number, number] =
      gridData.length > 0
        ? [
          gridData.reduce((sum, c) => sum + c.lngCenter, 0) / gridData.length,
          gridData.reduce((sum, c) => sum + c.latCenter, 0) / gridData.length,
        ]
        : defaultCenter;

    // Center on data center or default location
    map.setCenter(mapCenter);
    map.setZoom(11);

    // Set mapReady when style loads
    const handleStyleLoad = () => {
      setMapReady(true);
    };

    if (map.isStyleLoaded()) {
      setMapReady(true);
    } else {
      map.once("load", handleStyleLoad);
    }

    return () => {
      map.off("load", handleStyleLoad);
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  // Load districts when city changes
  useEffect(() => {
    let cancelled = false;
    const loadDistricts = async () => {
      try {
        const ds = await getCityDistricts(selectedCity);
        if (!cancelled) setDistricts(ds);
      } catch (e) {
        console.error("Failed to load districts", e);
        if (!cancelled) setDistricts([]);
      }
    };
    loadDistricts();
    return () => { cancelled = true; };
  }, [selectedCity]);

  // Load categories (discovery-enabled only)
  useEffect(() => {
    let cancelled = false;
    fetchCategories()
      .then((cats) => {
        if (!cancelled) {
          // Filter to discovery-enabled categories only
          const discoverable = cats.filter(cat => cat.isDiscoverable !== false);
          setCategoryOptions(discoverable);
        }
      })
      .catch((e) => {
        console.warn("Failed to load categories:", e);
        if (!cancelled) setCategoryOptions([]);
      });
    return () => { cancelled = true; };
  }, []);

  // Fetch coverage data when coverage is enabled or filters change
  // Note: This effect does NOT depend on map readiness - we can fetch data independently
  useEffect(() => {
    if (!showCoverage) {
      setGridData([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const fetchCoverage = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getDiscoveryCoverage(
          selectedCity,
          selectedDistrict || undefined,
          dateFrom || undefined,
          dateTo || undefined,
          selectedCategory || undefined
        );
        // console.debug("[DiscoveryCoverage] cells", data);
        if (!cancelled) {
          setGridData(data);
        }
      } catch (err) {
        console.error("Failed to fetch discovery coverage:", err);
        if (!cancelled) {
          setGridData([]);
          if (err instanceof Error && err.message.includes("timeout")) {
            setError("The coverage request timed out. Please try again.");
          } else {
            setError(err instanceof Error ? err.message : "Failed to load discovery coverage.");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCoverage();
    return () => { cancelled = true; };
  }, [showCoverage, selectedCity, selectedDistrict, dateFrom, dateTo, selectedCategory]);

  // Update map layers when grid data changes or coverage toggle changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // If coverage is disabled, hide layers instead of removing them
    if (!showCoverage) {
      try {
        // Guard against empty layer IDs to prevent "IDs can't be empty" errors
        if (HEATMAP_LAYER_ID && safeHasLayer(map, HEATMAP_LAYER_ID)) {
          map.setLayoutProperty(HEATMAP_LAYER_ID, "visibility", "none");
        }
        if (COVERAGE_LAYER_ID && safeHasLayer(map, COVERAGE_LAYER_ID)) {
          map.setLayoutProperty(COVERAGE_LAYER_ID, "visibility", "none");
        }
        if (COVERAGE_OUTLINE_LAYER_ID && safeHasLayer(map, COVERAGE_OUTLINE_LAYER_ID)) {
          map.setLayoutProperty(COVERAGE_OUTLINE_LAYER_ID, "visibility", "none");
        }
      } catch {
        // Ignore errors if layers don't exist
      }
      return;
    }

    // Wait for map to be ready before manipulating layers
    if (!mapReady) return;

    try {
      // Create point features for heatmap (always create, even if empty)
      const heatmapPoints: FeatureCollection<Point> = {
        type: "FeatureCollection",
        features: gridData.map((cell) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [cell.lngCenter, cell.latCenter],
          },
          properties: {
            weight: Math.max(1, cell.visitCount || 0), // Minimum weight of 1 for visibility
            district: cell.district,
            totalCalls: cell.totalCalls,
            visitCount: cell.visitCount,
            successfulCalls: cell.successfulCalls,
            error429: cell.error429,
            errorOther: cell.errorOther,
            firstSeenAt: cell.firstSeenAt,
            lastSeenAt: cell.lastSeenAt,
          },
        })),
      };

      // Create GeoJSON features from grid cells for polygon overlay (always create, even if empty)
      const features = gridData.map((cell) => ({
        type: "Feature" as const,
        geometry: createCellPolygon(cell.latCenter, cell.lngCenter, CELL_SPACING_M),
        properties: {
          latCenter: cell.latCenter,
          lngCenter: cell.lngCenter,
          totalCalls: cell.totalCalls,
          visitCount: cell.visitCount,
          successfulCalls: cell.successfulCalls,
          error429: cell.error429,
          errorOther: cell.errorOther,
          district: cell.district,
          firstSeenAt: cell.firstSeenAt,
          lastSeenAt: cell.lastSeenAt,
          color: getCellColorFromVisitCount(cell.visitCount || 0),
        },
      }));

      const geoJson: FeatureCollection<Polygon> = {
        type: "FeatureCollection",
        features,
      };

      // Add or update heatmap source
      const heatmapSource = map.getSource(HEATMAP_SOURCE_ID);
      if (heatmapSource && heatmapSource.type === "geojson") {
        (heatmapSource as mapboxgl.GeoJSONSource).setData(heatmapPoints);
      } else {
        map.addSource(HEATMAP_SOURCE_ID, {
          type: "geojson",
          data: heatmapPoints,
        });
      }

      // Add or update heatmap layer (always ensure it exists)
      if (!map.getLayer(HEATMAP_LAYER_ID)) {
        const heatmapLayerConfig: mapboxgl.Layer = {
          id: HEATMAP_LAYER_ID,
          type: "heatmap",
          source: HEATMAP_SOURCE_ID,
          paint: {
            "heatmap-weight": ["get", "weight"],
            "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 10, 3],
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0.0, "rgba(254,243,199,0.3)", // Light yellow with some opacity even at 0 density
              0.05, "#fef3c7", // Light yellow
              0.15, "#fdba74", // Orange
              0.4, "#f97316", // Stronger orange
              0.7, "#dc2626", // Red
              0.9, "#991b1b", // Dark red
            ],
            "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 2, 10, 25],
            "heatmap-opacity": 0.8,
          },
        };
        // NOTE: This was originally tuned for the "streets" style. Under Mapbox
        // Standard, "waterway-label" may not exist, but safeHasLayer() + fallback
        // to undefined keeps the heatmap insertion safe.
        // We do not modify any base style layers (place-labels, etc.) - all warnings
        // from sizerank/place-labels/terrain are from the Mapbox Standard style JSON itself.
        const heatmapBeforeId = safeHasLayer(map, "waterway-label")
          ? "waterway-label"
          : undefined;
        if (heatmapBeforeId) {
          map.addLayer(heatmapLayerConfig, heatmapBeforeId);
        } else {
          map.addLayer(heatmapLayerConfig);
        }
      } else {
        // Update source data for existing layer
        const existingSource = map.getSource(HEATMAP_SOURCE_ID);
        if (existingSource && existingSource.type === "geojson") {
          (existingSource as mapboxgl.GeoJSONSource).setData(heatmapPoints);
        }
      }

      // Set heatmap visibility based on showCoverage
      if (HEATMAP_LAYER_ID && safeHasLayer(map, HEATMAP_LAYER_ID)) {
        map.setLayoutProperty(HEATMAP_LAYER_ID, "visibility", "visible");
      }

      // Add or update polygon source
      const source = map.getSource(COVERAGE_SOURCE_ID);
      if (source && source.type === "geojson") {
        source.setData(geoJson);
      } else {
        map.addSource(COVERAGE_SOURCE_ID, {
          type: "geojson",
          data: geoJson,
        });
      }

      // Add fill layer if it doesn't exist
      if (!map.getLayer(COVERAGE_LAYER_ID)) {
        const coverageLayerConfig: mapboxgl.Layer = {
          id: COVERAGE_LAYER_ID,
          type: "fill",
          source: COVERAGE_SOURCE_ID,
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": 0.5,
          },
        };
        const coverageBeforeId = safeHasLayer(map, HEATMAP_LAYER_ID)
          ? HEATMAP_LAYER_ID
          : undefined;
        if (coverageBeforeId) {
          map.addLayer(coverageLayerConfig, coverageBeforeId);
        } else {
          map.addLayer(coverageLayerConfig);
        }
      } else {
        // Update source data for existing layer
        const existingSource = map.getSource(COVERAGE_SOURCE_ID);
        if (existingSource && existingSource.type === "geojson") {
          (existingSource as mapboxgl.GeoJSONSource).setData(geoJson);
        }
      }

      // Add outline layer if it doesn't exist
      if (!map.getLayer(COVERAGE_OUTLINE_LAYER_ID)) {
        const outlineLayerConfig: mapboxgl.Layer = {
          id: COVERAGE_OUTLINE_LAYER_ID,
          type: "line",
          source: COVERAGE_SOURCE_ID,
          paint: {
            "line-color": "#666",
            "line-width": 0.5,
            "line-opacity": 0.3,
          },
        };
        const outlineBeforeId = safeHasLayer(map, COVERAGE_LAYER_ID)
          ? COVERAGE_LAYER_ID
          : undefined;
        if (outlineBeforeId) {
          map.addLayer(outlineLayerConfig, outlineBeforeId);
        } else {
          map.addLayer(outlineLayerConfig);
        }
      }

      // Update grid overlay visibility based on toggle
      if (COVERAGE_LAYER_ID && safeHasLayer(map, COVERAGE_LAYER_ID)) {
        map.setLayoutProperty(COVERAGE_LAYER_ID, "visibility", showGridOverlay ? "visible" : "none");
      }
      if (COVERAGE_OUTLINE_LAYER_ID && safeHasLayer(map, COVERAGE_OUTLINE_LAYER_ID)) {
        map.setLayoutProperty(COVERAGE_OUTLINE_LAYER_ID, "visibility", showGridOverlay ? "visible" : "none");
      }

      // Set up click handlers (only once)
      const handleClick = (e: mapboxgl.MapLayerMouseEvent) => {
        if (!e.features || e.features.length === 0) return;

        const props = e.features[0].properties;
        if (!props) return;

        // Close existing popup
        if (popupRef.current) {
          popupRef.current.remove();
        }

        const visits = props.totalCalls ?? props.visitCount ?? 0;
        const firstSeen = formatDateOrDash(props.firstSeenAt);
        const lastSeen = formatDateOrDash(props.lastSeenAt);

        // Create new popup
        const popup = new Popup({ closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(
            `
            <div style="padding: 8px; min-width: 200px;">
              <div style="font-weight: 600; margin-bottom: 8px;">Grid Cell Coverage</div>
              <div style="font-size: 13px; line-height: 1.6;">
                ${props.district ? `<div><strong>District:</strong> ${props.district}</div>` : ""}
                <div><strong>Visits:</strong> ${visits}</div>
                <div><strong>Errors:</strong> 429: ${props.error429 || 0}, Other: ${props.errorOther || 0}</div>
                <div><strong>First Discovery:</strong> ${firstSeen}</div>
                <div><strong>Last Discovery:</strong> ${lastSeen}</div>
              </div>
            </div>
          `
          )
          .addTo(map);

        popupRef.current = popup;
      };

      // Remove existing handlers before adding new ones to avoid duplicates
      // Guard against empty layer IDs to prevent "IDs can't be empty" errors
      try {
        if (COVERAGE_LAYER_ID) map.off("click", COVERAGE_LAYER_ID);
        if (HEATMAP_LAYER_ID) map.off("click", HEATMAP_LAYER_ID);
        if (COVERAGE_LAYER_ID) map.on("click", COVERAGE_LAYER_ID, handleClick);
        if (HEATMAP_LAYER_ID) map.on("click", HEATMAP_LAYER_ID, handleClick);
      } catch (err) {
        console.warn("Failed to attach click handlers:", err);
      }

      // Add hover effect
      const handleMouseEnter = () => {
        map.getCanvas().style.cursor = "pointer";
      };
      const handleMouseLeave = () => {
        map.getCanvas().style.cursor = "";
      };

      try {
        if (COVERAGE_LAYER_ID) map.off("mouseenter", COVERAGE_LAYER_ID);
        if (HEATMAP_LAYER_ID) map.off("mouseenter", HEATMAP_LAYER_ID);
        if (COVERAGE_LAYER_ID) map.off("mouseleave", COVERAGE_LAYER_ID);
        if (HEATMAP_LAYER_ID) map.off("mouseleave", HEATMAP_LAYER_ID);
        if (COVERAGE_LAYER_ID) map.on("mouseenter", COVERAGE_LAYER_ID, handleMouseEnter);
        if (HEATMAP_LAYER_ID) map.on("mouseenter", HEATMAP_LAYER_ID, handleMouseEnter);
        if (COVERAGE_LAYER_ID) map.on("mouseleave", COVERAGE_LAYER_ID, handleMouseLeave);
        if (HEATMAP_LAYER_ID) map.on("mouseleave", HEATMAP_LAYER_ID, handleMouseLeave);
      } catch (err) {
        console.warn("Failed to attach hover handlers:", err);
      }
    } catch (err) {
      console.error("Failed to setup coverage layers:", err);
    }

    return () => {
      // Cleanup: remove event listeners when effect re-runs or unmounts
      if (map) {
        try {
          // Guard against empty layer IDs to prevent "IDs can't be empty" errors
          if (COVERAGE_LAYER_ID) map.off("click", COVERAGE_LAYER_ID);
          if (HEATMAP_LAYER_ID) map.off("click", HEATMAP_LAYER_ID);
          if (COVERAGE_LAYER_ID) map.off("mouseenter", COVERAGE_LAYER_ID);
          if (HEATMAP_LAYER_ID) map.off("mouseenter", HEATMAP_LAYER_ID);
          if (COVERAGE_LAYER_ID) map.off("mouseleave", COVERAGE_LAYER_ID);
          if (HEATMAP_LAYER_ID) map.off("mouseleave", HEATMAP_LAYER_ID);
        } catch {
          // Ignore errors
        }
      }
    };
  }, [showCoverage, mapReady, gridData, showGridOverlay]);

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-4 left-4 z-10 bg-white rounded-lg shadow-md p-4 space-y-2 max-w-xs">
        {/* City selector */}
        <div>
          <label className="block text-xs font-medium mb-1">City</label>
          {citiesLoading ? (
            <div className="text-xs text-muted-foreground py-1">Loading cities...</div>
          ) : citiesError ? (
            <div className="text-xs text-red-600 py-1">{citiesError}</div>
          ) : (
            <select
              value={selectedCity}
              onChange={(e) => onCityChange(e.target.value)}
              className="border rounded px-2 py-1 text-sm w-full"
              disabled={loading}
            >
              {cities
                .filter((city) => city.has_districts)
                .map((city) => (
                  <option key={city.city_key} value={city.city_key}>
                    {city.city_name}
                  </option>
                ))}
            </select>
          )}
        </div>

        {/* District selector */}
        <div>
          <label className="block text-xs font-medium mb-1">District</label>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="border rounded px-2 py-1 text-sm w-full"
            disabled={loading}
          >
            <option value="">All districts</option>
            {districts.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        {/* Category selector */}
        <div>
          <label className="block text-xs font-medium mb-1">Category</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="border rounded px-2 py-1 text-sm w-full"
            disabled={loading}
          >
            <option value="">All categories</option>
            {categoryOptions.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date range */}
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="block text-xs font-medium mb-1">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border rounded px-2 py-1 text-sm w-full"
              disabled={loading}
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium mb-1">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border rounded px-2 py-1 text-sm w-full"
              disabled={loading}
            />
          </div>
        </div>

        {/* Toggles */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <Button
            variant={showCoverage ? "default" : "outline"}
            size="sm"
            onClick={() => setShowCoverage(!showCoverage)}
            disabled={loading}
          >
            {loading ? "Loading..." : showCoverage ? "Hide coverage" : "Show coverage"}
          </Button>
          <label className="flex items-center gap-1 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={showGridOverlay}
              onChange={(e) => setShowGridOverlay(e.target.checked)}
              disabled={!showCoverage || loading}
            />
            Grid overlay
          </label>
        </div>

        {/* Loading state */}
        {loading && showCoverage && (
          <div className="text-xs text-blue-600 font-medium">
            Loading discovery coverage…
          </div>
        )}

        {/* Error state */}
        {error && <div className="text-xs text-red-600">{error}</div>}
      </div>

      {/* Map container with explicit height to ensure visibility */}
      <div
        ref={mapContainerRef}
        className="w-full h-[600px] min-h-[400px] rounded-lg border border-border bg-muted/20"
      />

      {/* Empty state overlay (only when no data and not loading) */}
      {!loading && !error && showCoverage && gridData.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-dashed border-border px-6 py-4 shadow-sm">
            <div className="text-sm font-medium text-muted-foreground text-center">
              No discovery coverage data for this selection yet.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


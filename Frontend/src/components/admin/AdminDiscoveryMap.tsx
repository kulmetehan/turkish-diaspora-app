import { useEffect, useRef, useState } from "react";
import mapboxgl, { Map as MapboxMap, Popup } from "mapbox-gl";
import type { FeatureCollection, Polygon } from "geojson";
import { initMap } from "@/lib/map/mapbox";
import { getDiscoveryGrid, type DiscoveryGridCell } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CONFIG } from "@/lib/config";

mapboxgl.accessToken = CONFIG.MAPBOX_TOKEN;

const COVERAGE_SOURCE_ID = "tda-discovery-coverage";
const COVERAGE_LAYER_ID = "tda-discovery-coverage-layer";
const COVERAGE_OUTLINE_LAYER_ID = "tda-discovery-coverage-outline";

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

function getCellColor(cell: DiscoveryGridCell): string {
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

export default function AdminDiscoveryMap() {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const [showCoverage, setShowCoverage] = useState(false);
  const [gridData, setGridData] = useState<DiscoveryGridCell[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = initMap(mapContainerRef.current);
    mapRef.current = map;

    // Center on Rotterdam
    map.setCenter([CONFIG.MAP_DEFAULT.lng, CONFIG.MAP_DEFAULT.lat]);
    map.setZoom(11);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Fetch grid data when coverage is enabled
  useEffect(() => {
    if (!showCoverage || !mapRef.current) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getDiscoveryGrid("rotterdam");
        setGridData(data);
      } catch (err) {
        console.error("Failed to fetch discovery grid:", err);
        // Handle timeout specifically
        if (err instanceof Error && err.message.includes("timeout")) {
          setError("The discovery grid request timed out. Please try again.");
        } else if (err instanceof DOMException && err.name === "AbortError") {
          setError("The discovery grid request was cancelled. Please try again.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load discovery grid.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [showCoverage]);

  // Update map layers when grid data changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!showCoverage || gridData.length === 0) {
      // Remove layers if coverage is disabled or no data
      try {
        if (map.getLayer(COVERAGE_LAYER_ID)) {
          map.removeLayer(COVERAGE_LAYER_ID);
        }
        if (map.getLayer(COVERAGE_OUTLINE_LAYER_ID)) {
          map.removeLayer(COVERAGE_OUTLINE_LAYER_ID);
        }
        if (map.getSource(COVERAGE_SOURCE_ID)) {
          map.removeSource(COVERAGE_SOURCE_ID);
        }
      } catch {
        // Ignore errors if layers don't exist
      }
      return;
    }

    // Wait for map to be ready
    const setupLayers = () => {
      if (!map.isStyleLoaded()) {
        map.once("style.load", setupLayers);
        return;
      }

      try {
        // Create GeoJSON features from grid cells
        const features = gridData.map((cell) => ({
          type: "Feature" as const,
          geometry: createCellPolygon(cell.latCenter, cell.lngCenter, CELL_SPACING_M),
          properties: {
            latCenter: cell.latCenter,
            lngCenter: cell.lngCenter,
            calls: cell.calls,
            inserts: cell.inserts,
            error429: cell.error429,
            errorOther: cell.errorOther,
            district: cell.district,
            color: getCellColor(cell),
          },
        }));

        const geoJson: FeatureCollection<Polygon> = {
          type: "FeatureCollection",
          features,
        };

        // Add or update source
        const source = map.getSource(COVERAGE_SOURCE_ID);
        if (source && source.type === "geojson") {
          source.setData(geoJson);
        } else {
          map.addSource(COVERAGE_SOURCE_ID, {
            type: "geojson",
            data: geoJson,
          });
        }

        // Add fill layer
        if (!map.getLayer(COVERAGE_LAYER_ID)) {
          map.addLayer({
            id: COVERAGE_LAYER_ID,
            type: "fill",
            source: COVERAGE_SOURCE_ID,
            paint: {
              "fill-color": ["get", "color"],
              "fill-opacity": 0.5,
            },
          });
        }

        // Add outline layer
        if (!map.getLayer(COVERAGE_OUTLINE_LAYER_ID)) {
          map.addLayer({
            id: COVERAGE_OUTLINE_LAYER_ID,
            type: "line",
            source: COVERAGE_SOURCE_ID,
            paint: {
              "line-color": "#666",
              "line-width": 0.5,
              "line-opacity": 0.3,
            },
          });
        }

        // Add click handler for tooltips
        map.on("click", COVERAGE_LAYER_ID, (e) => {
          if (!e.features || e.features.length === 0) return;

          const props = e.features[0].properties;
          if (!props) return;

          // Close existing popup
          if (popupRef.current) {
            popupRef.current.remove();
          }

          // Create new popup
          const popup = new Popup({ closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(
              `
              <div style="padding: 8px; min-width: 200px;">
                <div style="font-weight: 600; margin-bottom: 8px;">Grid Cell Stats</div>
                <div style="font-size: 13px; line-height: 1.6;">
                  <div><strong>Calls:</strong> ${props.calls}</div>
                  <div><strong>Inserts:</strong> ${props.inserts}</div>
                  <div><strong>429 Errors:</strong> ${props.error429}</div>
                  <div><strong>Other Errors:</strong> ${props.errorOther}</div>
                  ${props.district ? `<div><strong>District:</strong> ${props.district}</div>` : ""}
                </div>
              </div>
            `
            )
            .addTo(map);

          popupRef.current = popup;
        });

        // Add hover effect
        map.on("mouseenter", COVERAGE_LAYER_ID, () => {
          map.getCanvas().style.cursor = "pointer";
        });

        map.on("mouseleave", COVERAGE_LAYER_ID, () => {
          map.getCanvas().style.cursor = "";
        });
      } catch (err) {
        console.error("Failed to setup coverage layers:", err);
      }
    };

    setupLayers();

    return () => {
      // Cleanup: remove event listeners
      if (map) {
        try {
          map.off("click", COVERAGE_LAYER_ID);
          map.off("mouseenter", COVERAGE_LAYER_ID);
          map.off("mouseleave", COVERAGE_LAYER_ID);
        } catch {
          // Ignore errors
        }
      }
      if (popupRef.current) {
        popupRef.current.remove();
        popupRef.current = null;
      }
    };
  }, [showCoverage, gridData]);

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-4 left-4 z-10 bg-white rounded-lg shadow-md p-2">
        <Button
          variant={showCoverage ? "default" : "outline"}
          size="sm"
          onClick={() => setShowCoverage(!showCoverage)}
          disabled={loading}
        >
          {loading ? "Loading..." : showCoverage ? "Hide Coverage" : "Show Discovery Coverage"}
        </Button>
        {error && (
          <div className="mt-2 text-sm text-red-600">{error}</div>
        )}
        {!loading && !error && showCoverage && gridData.length === 0 && (
          <div className="mt-2 text-sm text-muted-foreground">
            No discovery data yet. The discovery bot may still be running.
          </div>
        )}
      </div>
      <div ref={mapContainerRef} className="w-full h-[600px] rounded-lg" />
    </div>
  );
}


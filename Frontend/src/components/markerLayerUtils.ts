import type { LocationMarker } from "@/api/fetchLocations";
import type { Map as MapboxMap } from "mapbox-gl";

const SRC_ID = "tda-locations";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_POINT = "tda-unclustered-point";
const L_HI = "tda-highlight";

export const MARKER_POINT_RADIUS = 6;
export const MARKER_POINT_STROKE_WIDTH = 2;
export const MARKER_POINT_OUTER_RADIUS = MARKER_POINT_RADIUS + MARKER_POINT_STROKE_WIDTH;
export const MARKER_POINT_DIAMETER = MARKER_POINT_OUTER_RADIUS * 2;

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
                    confidence: l.confidence_score ?? null,
                },
                geometry: {
                    type: "Point" as const,
                    coordinates: [l.lng as number, l.lat as number] as [number, number],
                },
            })),
    };
}

export function ensureBaseLayers(map: MapboxMap) {
    if (!map.getSource(SRC_ID)) {
        map.addSource(SRC_ID, {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50,
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
                "circle-color": [
                    "step",
                    ["get", "point_count"],
                    "#88c0ff",
                    25,
                    "#5599ff",
                    100,
                    "#2b6fe3",
                ],
                "circle-radius": [
                    "step",
                    ["get", "point_count"],
                    16,
                    25,
                    22,
                    100,
                    28,
                ],
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

    if (!map.getLayer(L_POINT)) {
        map.addLayer({
            id: L_POINT,
            type: "circle",
            source: SRC_ID,
            filter: ["!", ["has", "point_count"]],
            paint: {
                "circle-color": [
                    "case",
                    ["boolean", ["feature-state", "selected"], false],
                    "#22c55e",
                    "#e11d48",
                ],
                "circle-radius": MARKER_POINT_RADIUS,
                "circle-stroke-color": [
                    "case",
                    ["boolean", ["feature-state", "selected"], false],
                    "#14532d",
                    "#fff",
                ],
                "circle-stroke-width": MARKER_POINT_STROKE_WIDTH,
            },
        });
    }

    if (!map.getLayer(L_HI)) {
        map.addLayer({
            id: L_HI,
            type: "circle",
            source: SRC_ID,
            filter: [
                "all",
                ["!", ["has", "point_count"]],
                ["==", ["get", "id"], "__none__"],
            ],
            paint: {
                "circle-color": "#22c55e",
                "circle-radius": 10,
                "circle-stroke-color": "#14532d",
                "circle-stroke-width": 2,
            },
        });
    }
}

export const MarkerLayerIds = {
    SRC_ID,
    L_CLUSTER,
    L_CLUSTER_COUNT,
    L_POINT,
    L_HI,
} as const;


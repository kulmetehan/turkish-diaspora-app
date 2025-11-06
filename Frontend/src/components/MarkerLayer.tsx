// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import type {
    LngLatLike,
    MapboxGeoJSONFeature,
    Map as MapboxMap,
} from "mapbox-gl";
import { useEffect, useMemo, useRef } from "react";

type Props = {
    map: MapboxMap;
    locations: LocationMarker[];
    selectedId: string | null;
    onSelect?: (id: string) => void;
};

// Stable IDs for source/layers
const SRC_ID = "tda-locations";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_POINT = "tda-unclustered-point";
const L_HI = "tda-highlight";

// Safely check if style exists on the map
function hasStyleObject(m: MapboxMap) {
    try {
        const s = m.getStyle?.();
        return !!s && !!(s as any).sources;
    } catch {
        return false;
    }
}

export default function MarkerLayer({ map, locations, selectedId, onSelect }: Props) {
    // Have we already added source/layers to THIS map instance?
    const layersReady = useRef(false);
    // Have we already attached event handlers to THIS map instance?
    const handlersReady = useRef(false);
    // Keep latest onSelect so handlers always call the newest callback
    const onSelectRef = useRef<typeof onSelect>(onSelect);
    useEffect(() => {
        onSelectRef.current = onSelect;
    }, [onSelect]);

    // Build GeoJSON for current locations
    const data = useMemo(() => {
        return {
            type: "FeatureCollection" as const,
            features: locations
                .filter((l) => typeof l.lat === "number" && typeof l.lng === "number")
                .map((l) => ({
                    type: "Feature" as const,
                    id: String(l.id), // Top-level feature ID for Mapbox feature tracking
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
    }, [locations]);

    // 1. Create source + layers once per map
    useEffect(() => {
        function tryInitLayers() {
            if (layersReady.current) return;

            // Source
            if (!map.getSource(SRC_ID)) {
                map.addSource(SRC_ID, {
                    type: "geojson",
                    data: { type: "FeatureCollection", features: [] },
                    cluster: true,
                    clusterMaxZoom: 14,
                    clusterRadius: 50,
                } as any);
            }

            // Cluster circles
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

            // Cluster count labels
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

            // Individual point markers
            if (!map.getLayer(L_POINT)) {
                map.addLayer({
                    id: L_POINT,
                    type: "circle",
                    source: SRC_ID,
                    filter: ["!", ["has", "point_count"]],
                    paint: {
                        "circle-color": "#e11d48",
                        "circle-radius": 6,
                        "circle-stroke-color": "#fff",
                        "circle-stroke-width": 2,
                    },
                });
            }

            // Highlight ring for selected point
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

            layersReady.current = true;
        }

        if (!hasStyleObject(map)) {
            // Style not ready yet: wait for load, then init
            const handleLoad = () => {
                tryInitLayers();
            };
            map.once("load", handleLoad);
            return () => {
                try {
                    map.off("load", handleLoad);
                } catch {
                    /* ignore */
                }
            };
        }

        tryInitLayers();
    }, [map]);

    // 2. Sync GeoJSON data when locations change
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        const src: any = map.getSource(SRC_ID);
        if (src && src.setData) {
            src.setData(data as any);
        }
    }, [map, data, locations]);

    // 3. Attach interactivity handlers once
    useEffect(() => {
        if (!layersReady.current) return;
        if (handlersReady.current) return;

        const onClusterClick = (e: any) => {
            const feats = map.queryRenderedFeatures(e.point, {
                layers: [L_CLUSTER],
            }) as MapboxGeoJSONFeature[] | undefined;
            const clusterId = feats?.[0]?.properties?.cluster_id;
            if (clusterId == null) return;
            const src: any = map.getSource(SRC_ID);
            if (!src?.getClusterExpansionZoom) return;
            src.getClusterExpansionZoom(clusterId, (err: unknown, zoom: number) => {
                if (err) return;
                const center = (feats![0].geometry as any).coordinates as LngLatLike;
                map.easeTo({ center, zoom });
            });
        };

        const onPointClick = (e: any) => {
            const feats = map.queryRenderedFeatures(e.point, {
                layers: [L_POINT],
            }) as MapboxGeoJSONFeature[] | undefined;
            const id = feats?.[0]?.properties?.id as string | undefined;
            if (id && onSelectRef.current) {
                onSelectRef.current(id);
            }
        };

        const onMouseMove = (e: any) => {
            try {
                const feats = map.queryRenderedFeatures(e.point, {
                    layers: [L_POINT, L_CLUSTER, L_CLUSTER_COUNT],
                }) as any[];
                const hit = Array.isArray(feats) && feats.length > 0;
                map.getCanvas().style.cursor = hit ? "pointer" : "";
            } catch {
                /* ignore */
            }
        };

        const forcePointer = () => {
            try {
                map.getCanvas().style.cursor = "pointer";
            } catch {
                /* ignore */
            }
        };
        const clearPointer = () => {
            try {
                map.getCanvas().style.cursor = "";
            } catch {
                /* ignore */
            }
        };

        map.on("click", L_CLUSTER, onClusterClick as any);
        map.on("click", L_POINT, onPointClick as any);
        map.on("mousemove", onMouseMove as any);

        map.on("mouseenter", L_POINT, forcePointer as any);
        map.on("mouseleave", L_POINT, clearPointer as any);
        map.on("mouseenter", L_CLUSTER, forcePointer as any);
        map.on("mouseleave", L_CLUSTER, clearPointer as any);

        handlersReady.current = true;

        // IMPORTANT:
        // We intentionally do NOT clean these up in a return() cleanup.
        // The map instance persists across React StrictMode fake-unmount/remount,
        // so removing handlers here would break interactivity in dev.
    }, [map]);

    // 4. Sync highlight ring with selectedId
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        if (!map.getLayer(L_HI)) return;
        const selId = selectedId ?? "__none__";
        try {
            map.setFilter(L_HI, [
                "all",
                ["!", ["has", "point_count"]],
                ["==", ["get", "id"], selId],
            ]);
        } catch {
            /* ignore */
        }
    }, [map, selectedId, locations]);

    return null;
}


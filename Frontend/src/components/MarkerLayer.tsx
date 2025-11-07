// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import type {
    LngLatLike,
    MapboxGeoJSONFeature,
    Map as MapboxMap,
} from "mapbox-gl";
import { useCallback, useEffect, useMemo, useRef } from "react";

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

    const lastEnsureTsRef = useRef<number>(0);
    const pendingSetDataRef = useRef<(() => void) | null>(null);

    // Build GeoJSON for current locations
    const data = useMemo(() => {
        const features = locations
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
            }));

        // Debug: log feature count and sample IDs (only in dev)
        if (import.meta.env.DEV && features.length > 0) {
            console.debug(`[MarkerLayer] Built ${features.length} features. Sample IDs:`,
                features.slice(0, 3).map(f => f.id));
        }

        return {
            type: "FeatureCollection" as const,
            features,
        };
    }, [locations]);

    // 1. Ensure source and layers exist (called on init and style reload)
    // Use useCallback to create a stable function reference
    const ensureSourceAndLayers = useCallback(() => {
        if (!hasStyleObject(map)) return;

        const now = typeof performance !== "undefined" ? performance.now() : Date.now();
        if (lastEnsureTsRef.current && now - lastEnsureTsRef.current < 50) {
            if (import.meta.env.DEV) {
                console.debug(
                    `[MarkerLayer] ensureSourceAndLayers: skipped (debounced ${Math.round(now - lastEnsureTsRef.current)}ms)`
                );
            }
            return;
        }
        lastEnsureTsRef.current = now;

        const hadSource = !!map.getSource(SRC_ID);
        const hadCluster = !!map.getLayer(L_CLUSTER);
        const hadClusterCount = !!map.getLayer(L_CLUSTER_COUNT);
        const hadPoint = !!map.getLayer(L_POINT);
        const hadHighlight = !!map.getLayer(L_HI);

        let addedSource = false;
        let addedCluster = false;
        let addedClusterCount = false;
        let addedPoint = false;
        let addedHighlight = false;

        if (!hadSource) {
            map.addSource(SRC_ID, {
                type: "geojson",
                data: { type: "FeatureCollection", features: [] },
                cluster: true,
                clusterMaxZoom: 14,
                clusterRadius: 50,
            } as any);
            addedSource = true;
        }

        if (!hadCluster) {
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
            addedCluster = true;
        }

        if (!hadClusterCount) {
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
            addedClusterCount = true;
        }

        if (!hadPoint) {
            map.addLayer({
                id: L_POINT,
                type: "circle",
                source: SRC_ID,
                filter: ["!", ["has", "point_count"]],
                paint: {
                    "circle-color": "#ff6600", // Orange for visibility
                    "circle-radius": 5,
                    "circle-opacity": 0.9,
                    "circle-stroke-color": "#fff",
                    "circle-stroke-width": 1,
                },
            });
            addedPoint = true;
        }

        if (!hadHighlight) {
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
            addedHighlight = true;
        }

        // Keep markers & clusters above base layers when first created
        try {
            if (addedCluster) map.moveLayer(L_CLUSTER);
            if (addedClusterCount) map.moveLayer(L_CLUSTER_COUNT);
            if (addedPoint) map.moveLayer(L_POINT);
            if (addedHighlight) map.moveLayer(L_HI);
        } catch {
            // moveLayer may fail if style not fully ready; ignore
        }

        if (import.meta.env.DEV) {
            console.debug(
                "[MarkerLayer] ensureSourceAndLayers: src=%s (added=%s) cluster=%s count=%s point=%s highlight=%s",
                hadSource ? "present" : "absent",
                addedSource,
                hadCluster ? "present" : addedCluster ? "added" : "absent",
                hadClusterCount ? "present" : addedClusterCount ? "added" : "absent",
                hadPoint ? "present" : addedPoint ? "added" : "absent",
                hadHighlight ? "present" : addedHighlight ? "added" : "absent"
            );
        }
    }, [map]);

    // 2. Create source + layers once per map, and re-attach on style reload
    useEffect(() => {
        if (!map) return;

        const initLayers = () => {
            ensureSourceAndLayers();
            layersReady.current = true;
        };

        if (!map.isStyleLoaded()) {
            const handleLoad = () => {
                if (import.meta.env.DEV) {
                    console.debug("[MarkerLayer] map load → init layers");
                }
                initLayers();
            };
            map.once("load", handleLoad);
        } else {
            initLayers();
        }

        const handleStyleLoad = () => {
            layersReady.current = false;
            ensureSourceAndLayers();
            layersReady.current = true;
        };

        const handleStyleData = () => {
            ensureSourceAndLayers();
        }; // debounced inside ensureSourceAndLayers()

        map.on("style.load", handleStyleLoad);
        map.on("styledata", handleStyleData);

        return () => {
            try {
                map.off("style.load", handleStyleLoad);
                map.off("styledata", handleStyleData);
            } catch {
                /* ignore */
            }
        };
    }, [map, ensureSourceAndLayers]);

    // 3. Sync GeoJSON data when locations change
    // Use a ref to track the last data to avoid unnecessary updates
    // Compare by feature count and a stable hash of IDs (more efficient than full JSON stringify)
    const lastDataHashRef = useRef<string | null>(null);
    useEffect(() => {
        if (!map) return;
        let cancelled = false;

        const applyData = () => {
            if (cancelled) return;
            if (!hasStyleObject(map)) return;

            ensureSourceAndLayers();
            const src: any = map.getSource(SRC_ID);
            if (!src || !src.setData) {
                if (import.meta.env.DEV) {
                    console.warn("[MarkerLayer] setData: source unavailable");
                }
                return;
            }

            const featureCount = data.features.length;
            const ids = data.features.map(f => String(f.id || f.properties?.id || ""))
                .sort()
                .join(',');
            const dataHash = `${featureCount}:${ids}`;

            if (lastDataHashRef.current === dataHash) {
                return;
            }
            lastDataHashRef.current = dataHash;

            if (featureCount === 0) {
                src.setData({ type: "FeatureCollection", features: [] } as any);
                if (import.meta.env.DEV) {
                    console.debug("[MarkerLayer] setData: features=0 (cleared)");
                }
                return;
            }

            const featuresWithIds = data.features.map(f => {
                if (!f.id && f.properties?.id) {
                    return { ...f, id: String(f.properties.id) };
                }
                return f;
            });

            src.setData({
                ...data,
                features: featuresWithIds,
            } as any);

            if (import.meta.env.DEV) {
                const topIds = featuresWithIds.slice(0, 3).map(f => f.id);
                console.debug("[MarkerLayer] setData: features=%d ids=%o", featuresWithIds.length, topIds);
            }
        };

        const scheduleApply = () => {
            if (cancelled) return;

            if (!map.isStyleLoaded()) {
                if (!pendingSetDataRef.current) {
                    if (import.meta.env.DEV) {
                        console.debug("[MarkerLayer] setData waiting for style load…");
                    }
                    pendingSetDataRef.current = () => {
                        if (cancelled) return;
                        pendingSetDataRef.current = null;
                        applyData();
                    };
                    map.once("styledata", () => {
                        const fn = pendingSetDataRef.current;
                        pendingSetDataRef.current = null;
                        if (fn) fn();
                    });
                }
                return;
            }

            applyData();
        };

        scheduleApply();

        return () => {
            cancelled = true;
            pendingSetDataRef.current = null;
        };
    }, [map, data, locations, ensureSourceAndLayers]);

    // 4. Attach interactivity handlers once
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

    // 5. Sync highlight ring with selectedId
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


// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import type {
    LngLatLike,
    MapboxGeoJSONFeature,
    Map as MapboxMap,
} from "mapbox-gl";
import { useCallback, useEffect, useMemo, useRef, type MutableRefObject } from "react";

type Props = {
    map: MapboxMap;
    locations: LocationMarker[];
    selectedId: string | null;
    onSelect?: (id: string) => void;
    styleReady: boolean;
    styleVersion: number;
};

// Stable IDs for source/layers
const SRC_ID = "tda-locations";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_POINT = "tda-unclustered-point";
const L_HI = "tda-highlight";

type EnsureParams = {
    map: MapboxMap;
    styleReady: boolean;
    styleVersion: number;
    attachedStyleVersionRef: MutableRefObject<number | null>;
};

export function ensureSourceAndLayersOnce({ map, styleReady, styleVersion, attachedStyleVersionRef }: EnsureParams): boolean {
    if (!styleReady) {
        if (import.meta.env.DEV) {
            console.debug("[MarkerLayer] skip: style not ready");
        }
        return false;
    }

    if (attachedStyleVersionRef.current === styleVersion) {
        return true;
    }

    if (!map.isStyleLoaded()) {
        if (import.meta.env.DEV) {
            console.debug("[MarkerLayer] skip: style not fully loaded yet");
        }
        return false;
    }

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
                "circle-color": "#ff6600",
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

    try {
        if (addedCluster) map.moveLayer(L_CLUSTER);
        if (addedClusterCount) map.moveLayer(L_CLUSTER_COUNT);
        if (addedPoint) map.moveLayer(L_POINT);
        if (addedHighlight) map.moveLayer(L_HI);
    } catch {
        /* ignore */
    }

    attachedStyleVersionRef.current = styleVersion;

    if (import.meta.env.DEV) {
        console.debug(
            "[MarkerLayer] attach styleVersion=%d (source=%s cluster=%s count=%s point=%s highlight=%s)",
            styleVersion,
            hadSource ? "existing" : addedSource ? "added" : "missing",
            hadCluster ? "existing" : addedCluster ? "added" : "missing",
            hadClusterCount ? "existing" : addedClusterCount ? "added" : "missing",
            hadPoint ? "existing" : addedPoint ? "added" : "missing",
            hadHighlight ? "existing" : addedHighlight ? "added" : "missing"
        );
    }

    return true;
}

export default function MarkerLayer({ map, locations, selectedId, onSelect, styleReady, styleVersion }: Props) {
    // Have we already added source/layers for the current style version?
    const layersReady = useRef(false);
    const attachedStyleVersionRef = useRef<number | null>(null);
    // Have we already attached event handlers to THIS map instance?
    const handlersReady = useRef(false);
    // Keep latest onSelect so handlers always call the newest callback
    const onSelectRef = useRef<typeof onSelect>(onSelect);
    useEffect(() => {
        onSelectRef.current = onSelect;
    }, [onSelect]);

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

    // 1. Ensure source and layers exist (once per style version)
    const ensureLayers = useCallback(() => ensureSourceAndLayersOnce({
        map,
        styleReady,
        styleVersion,
        attachedStyleVersionRef,
    }), [map, styleReady, styleVersion]);

    useEffect(() => {
        if (!styleReady) {
            layersReady.current = false;
            return;
        }
        const attached = ensureLayers();
        if (attached) {
            layersReady.current = true;
        }
    }, [styleReady, styleVersion, ensureLayers]);

    // 2. Sync GeoJSON data when locations change
    const lastDataHashRef = useRef<string | null>(null);
    useEffect(() => {
        if (!map) return;
        let cancelled = false;

        const applyData = () => {
            if (cancelled) return;
            if (!styleReady || attachedStyleVersionRef.current !== styleVersion) {
                if (import.meta.env.DEV) {
                    console.debug("[MarkerLayer] skip: style not ready (setData)");
                }
                return;
            }

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
                .join(",");
            const dataHash = `${featureCount}:${ids}`;

            if (lastDataHashRef.current === dataHash) {
                return;
            }
            lastDataHashRef.current = dataHash;

            if (featureCount === 0) {
                src.setData({ type: "FeatureCollection", features: [] } as any);
                if (import.meta.env.DEV) {
                    console.debug("[MarkerLayer] setData features=0 (cleared)");
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
                console.debug("[MarkerLayer] setData features=%d ids=%o", featuresWithIds.length, topIds);
            }
        };

        if (!styleReady) {
            if (import.meta.env.DEV) {
                console.debug("[MarkerLayer] skip: style not ready (schedule setData)");
            }
            return () => {
                cancelled = true;
            };
        }

        if (!ensureLayers()) {
            if (import.meta.env.DEV) {
                console.debug("[MarkerLayer] awaiting ensureSourceAndLayersOnce before setData");
            }
            return () => {
                cancelled = true;
            };
        }

        applyData();

        return () => {
            cancelled = true;
        };
    }, [map, data, styleReady, styleVersion, ensureLayers]);

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
    }, [map, styleReady, styleVersion]);

    // 5. Sync highlight ring with selectedId
    useEffect(() => {
        if (!layersReady.current) return;
        if (!styleReady || attachedStyleVersionRef.current !== styleVersion) return;
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
    }, [map, selectedId, locations, styleReady, styleVersion]);

    return null;
}


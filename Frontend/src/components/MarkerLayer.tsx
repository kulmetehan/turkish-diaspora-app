// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import { buildMarkerGeoJSON, ensureBaseLayers, MarkerLayerIds } from "@/components/markerLayerUtils";
import { safeHasLayer } from "@/lib/map/mapbox";
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
    onClusterFocus?: (center: LngLatLike, zoom: number) => void;
    visible?: boolean; // Control layer visibility
};

// Stable IDs for source/layers
const { SRC_ID, L_CLUSTER, L_CLUSTER_COUNT, L_POINT, L_HALO, L_POINT_FALLBACK, L_HI } = MarkerLayerIds;

// Safely check if style exists on the map
function hasStyleObject(m: MapboxMap) {
    try {
        const s = m.getStyle?.();
        return !!s && !!(s as any).sources;
    } catch {
        return false;
    }
}

export default function MarkerLayer({ map, locations, selectedId, onSelect, onClusterFocus, visible = true }: Props) {
    // Have we already added source/layers to THIS map instance?
    const layersReady = useRef(false);
    // Have we already attached event handlers to THIS map instance?
    const handlersReady = useRef(false);
    // Keep track of currently selected feature id for feature-state
    const featureStateRef = useRef<string | null>(null);
    // Keep latest onSelect so handlers always call the newest callback
    const onSelectRef = useRef<typeof onSelect>(onSelect);
    useEffect(() => {
        onSelectRef.current = onSelect;
    }, [onSelect]);

    // Build GeoJSON for current locations
    const data = useMemo(() => {
        const geoJson = buildMarkerGeoJSON(locations);
        return geoJson;
    }, [locations]);

    // 1. Create source + layers once per map
    useEffect(() => {
        function tryInitLayers() {
            if (layersReady.current) return;

            ensureBaseLayers(map);
            // Verify layers were created (defensive check)
            if (map.getLayer(L_CLUSTER) && map.getLayer(L_POINT)) {
                layersReady.current = true;
            } else {
                console.warn("[MarkerLayer] Some marker layers failed to initialize");
                // Still mark as ready to avoid blocking, but log warning
                layersReady.current = true;
            }
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
    }, [map, onClusterFocus]);

    // 2. Sync GeoJSON data when locations change
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        const src: any = map.getSource(SRC_ID);
        if (src && src.setData) {
            src.setData(data as any);
        }
    }, [map, data, locations]);

    // 2.5. Control layer visibility
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        
        const layers = [L_CLUSTER, L_POINT, L_HALO, L_POINT_FALLBACK];
        const visibility = visible ? "visible" : "none";
        
        console.debug("[MarkerLayer] Setting visibility to", visibility, "for", layers.length, "layers");
        
        layers.forEach((layerId) => {
            try {
                if (map.getLayer(layerId)) {
                    map.setLayoutProperty(layerId, "visibility", visibility);
                }
            } catch (error) {
                console.error("[MarkerLayer] Error setting visibility for", layerId, error);
            }
        });
    }, [map, visible]);

    // 3. Attach interactivity handlers once
    useEffect(() => {
        if (!layersReady.current) return;
        if (handlersReady.current) return;

        const onClusterClick = (e: any) => {
            // Defensive: check if cluster layer exists before querying
            if (!map.getLayer(L_CLUSTER)) return;

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
                if (onClusterFocus) {
                    onClusterFocus(center, zoom);
                    return;
                }
                map.easeTo({ center, zoom });
            });
        };

        const onPointClick = (e: any) => {
            // Defensive: check if point layer exists before querying
            if (!map.getLayer(L_POINT)) return;

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
                // Defensive: check if layers exist before querying to avoid console spam
                // If layers are not present yet (e.g. cluster layer failed to init),
                // don't query features
                const hasClusterLayer = !!map.getLayer(L_CLUSTER);
                const hasPointLayer = !!map.getLayer(L_POINT);

                if (!hasClusterLayer && !hasPointLayer) {
                    return;
                }

                const queryLayers = [
                    ...(hasClusterLayer ? [L_CLUSTER] : []),
                    ...(hasPointLayer ? [L_POINT] : []),
                ];

                if (queryLayers.length === 0) return;

                const feats = map.queryRenderedFeatures(e.point, {
                    layers: queryLayers,
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

        // Guard against empty layer IDs to prevent "IDs can't be empty" errors
        if (L_CLUSTER) map.on("click", L_CLUSTER, onClusterClick as any);
        if (L_POINT) map.on("click", L_POINT, onPointClick as any);
        map.on("mousemove", onMouseMove as any);

        if (L_POINT) map.on("mouseenter", L_POINT, forcePointer as any);
        if (L_POINT) map.on("mouseleave", L_POINT, clearPointer as any);
        if (L_CLUSTER) map.on("mouseenter", L_CLUSTER, forcePointer as any);
        if (L_CLUSTER) map.on("mouseleave", L_CLUSTER, clearPointer as any);

        handlersReady.current = true;

        // IMPORTANT:
        // We intentionally do NOT clean these up in a return() cleanup.
        // The map instance persists across React StrictMode fake-unmount/remount,
        // so removing handlers here would break interactivity in dev.
    }, [map]);

    // 4. Sync feature-state selection with selectedId
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        const nextId = typeof selectedId === "string" ? selectedId : selectedId != null ? String(selectedId) : null;
        const prevId = featureStateRef.current;

        if (prevId && prevId !== nextId) {
            try {
                map.removeFeatureState({ source: SRC_ID, id: prevId }, "selected");
            } catch {
                /* ignore */
            }
        }

        if (nextId) {
            try {
                map.setFeatureState({ source: SRC_ID, id: nextId }, { selected: true });
            } catch {
                /* ignore */
            }
        }

        featureStateRef.current = nextId;
    }, [map, selectedId, data]);

    useEffect(() => {
        if (!layersReady.current) return;
        const handleStyleData = () => {
            if (!featureStateRef.current) return;
            try {
                map.setFeatureState({ source: SRC_ID, id: featureStateRef.current }, { selected: true });
            } catch {
                /* ignore */
            }
        };
        map.on("styledata", handleStyleData);
        return () => {
            try {
                map.off("styledata", handleStyleData);
            } catch {
                /* ignore */
            }
        };
    }, [map]);

    useEffect(() => {
        return () => {
            if (!featureStateRef.current) return;
            try {
                map.removeFeatureState({ source: SRC_ID, id: featureStateRef.current }, "selected");
            } catch {
                /* ignore */
            }
            featureStateRef.current = null;
        };
    }, [map]);

    // 5. Sync highlight ring with selectedId
    useEffect(() => {
        if (!layersReady.current) return;
        if (!hasStyleObject(map)) return;
        // Guard against empty/undefined layer IDs to prevent "IDs can't be empty" errors
        if (!L_HI || !safeHasLayer(map, L_HI)) return;
        const selId = selectedId != null ? String(selectedId) : "__none__";
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


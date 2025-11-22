// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import { buildMarkerGeoJSON, ensureBaseLayers, MarkerLayerIds } from "@/components/markerLayerUtils";
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
};

// Stable IDs for source/layers
const { SRC_ID, L_CLUSTER, L_CLUSTER_COUNT, L_POINT, L_HI } = MarkerLayerIds;

// Safely check if style exists on the map
function hasStyleObject(m: MapboxMap) {
    try {
        const s = m.getStyle?.();
        return !!s && !!(s as any).sources;
    } catch {
        return false;
    }
}

export default function MarkerLayer({ map, locations, selectedId, onSelect, onClusterFocus }: Props) {
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
    const data = useMemo(() => buildMarkerGeoJSON(locations), [locations]);

    // 1. Create source + layers once per map
    useEffect(() => {
        function tryInitLayers() {
            if (layersReady.current) return;

            ensureBaseLayers(map);
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
                if (onClusterFocus) {
                    onClusterFocus(center, zoom);
                    return;
                }
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
        if (!map.getLayer(L_HI)) return;
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


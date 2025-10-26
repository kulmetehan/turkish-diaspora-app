// src/components/MarkerLayer.tsx
import type { LocationMarker } from "@/api/fetchLocations";
import type { LngLatLike, MapboxGeoJSONFeature, Map as MapboxMap } from "mapbox-gl";
import { useEffect, useMemo, useRef } from "react";

type Props = {
  map: MapboxMap;
  locations: LocationMarker[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
};

/** IDs voor source & layers (éénmaal gebruiken in hele app) */
const SRC_ID = "tda-locations";
const L_CLUSTER = "tda-clusters";
const L_CLUSTER_COUNT = "tda-cluster-count";
const L_POINT = "tda-unclustered-point";
const L_HI = "tda-highlight";

/** Veilige style-checks zonder console-warnings */
const hasStyleObject = (m: MapboxMap) => {
  try {
    const s = m.getStyle();
    return !!s && !!(s as any).sources;
  } catch {
    return false;
  }
};

export default function MarkerLayer({ map, locations, selectedId, onSelect }: Props) {
  const initialized = useRef(false);
  const handlersAttached = useRef(false);
  const onSelectRef = useRef<typeof onSelect>(onSelect);
  // keep latest onSelect without re-binding map listeners
  useEffect(() => { onSelectRef.current = onSelect; }, [onSelect]);

  /** Minimale “signatuur” zodat setData alleen triggert als de set echt wijzigt */
  const idsSignature = useMemo(() => locations.map((l) => l.id).join(","), [locations]);

  /** GeoJSON om in de source te stoppen */
  const data = useMemo(
    () => ({
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
    }),
    [locations]
  );

  /** Eénmalige init + handlers; persist across selects/deselects */
  useEffect(() => {
    if (initialized.current) return;

    const attachAll = () => {
      // Ensure style is loaded
      if (!map.isStyleLoaded?.()) {
        map.once("style.load", attachAll as any);
        return;
      }

      // Add source if missing
      if (!map.getSource(SRC_ID)) {
        map.addSource(SRC_ID, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] } as any,
          cluster: true,
          clusterMaxZoom: 14,
          clusterRadius: 50,
        });
      }

      // Layers
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
          layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 },
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
            "circle-color": "#e11d48",
            "circle-radius": 6,
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 2,
          },
        });
      }
      if (!map.getLayer(L_HI)) {
        map.addLayer({
          id: L_HI,
          type: "circle",
          source: SRC_ID,
          filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "id"], "__none__"]],
          paint: {
            "circle-color": "#22c55e",
            "circle-radius": 10,
            "circle-stroke-color": "#14532d",
            "circle-stroke-width": 2,
          },
        });
      }

      // Stable handlers using refs
      const clusterClick = (e: any) => {
        const feats = map.queryRenderedFeatures(e.point, { layers: [L_CLUSTER] }) as
          | MapboxGeoJSONFeature[]
          | undefined;
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

      const pointClick = (e: any) => {
        const feats = map.queryRenderedFeatures(e.point, { layers: [L_POINT] }) as
          | MapboxGeoJSONFeature[]
          | undefined;
        const id = feats?.[0]?.properties?.id as string | undefined;
        if (id) onSelectRef.current?.(id);
      };

      const mouseMove = (e: any) => {
        try {
          const feats = map.queryRenderedFeatures(e.point, { layers: [L_POINT, L_CLUSTER, L_CLUSTER_COUNT] }) as any[];
          const hit = Array.isArray(feats) && feats.length > 0;
          map.getCanvas().style.cursor = hit ? "pointer" : "";
        } catch { }
      };

      if (!handlersAttached.current) {
        map.on("click", L_CLUSTER, clusterClick as any);
        map.on("click", L_POINT, pointClick as any);
        map.on("mousemove", mouseMove as any);
        handlersAttached.current = true;
      }

      initialized.current = true;
    };

    if (!hasStyleObject(map)) {
      map.once("load", attachAll as any);
      return () => {
        try { map.off("load", attachAll as any); } catch { }
      };
    }

    attachAll();

    return () => {
      // Only on unmount
      if (handlersAttached.current) {
        try {
          map.off("click", L_CLUSTER, clusterClick as any);
          map.off("click", L_POINT, pointClick as any);
          map.off("mousemove", mouseMove as any);
        } catch { }
        handlersAttached.current = false;
      }
    };
  }, [map]);

  /** Alleen data updaten wanneer de set wijzigt */
  useEffect(() => {
    if (!initialized.current) return;
    if (!hasStyleObject(map)) return;

    const src: any = map.getSource(SRC_ID);
    if (src?.setData) {
      src.setData(data as any);
    }
  }, [map, idsSignature, data]);

  /** Alleen highlight-filter aanpassen op selectie */
  useEffect(() => {
    if (!initialized.current) return;
    if (!hasStyleObject(map)) return;
    if (!map.getLayer(L_HI)) return;

    const id = selectedId ?? "__none__";
    try {
      map.setFilter(L_HI, ["all", ["!", ["has", "point_count"]], ["==", ["get", "id"], id]]);
    } catch { }
  }, [map, selectedId]);

  return null;
}

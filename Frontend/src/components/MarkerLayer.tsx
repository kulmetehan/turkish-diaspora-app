// src/components/MarkerLayer.tsx
import { useEffect, useMemo, useRef } from "react";
import type { Map as MapboxMap, MapboxGeoJSONFeature, LngLatLike } from "mapbox-gl";
import type { Location } from "@/lib/api/location";

type Props = {
  map: MapboxMap;
  locations: Location[];
  selectedId: number | null;
  onSelect?: (id: number) => void;
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

  /** Minimale “signatuur” zodat setData alleen triggert als de set echt wijzigt */
  const idsSignature = useMemo(() => locations.map((l) => l.id).join(","), [locations]);

  /** GeoJSON om in de source te stoppen */
  const data = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: locations.map((l) => ({
        type: "Feature" as const,
        properties: {
          id: l.id,
          name: l.name,
          category: l.category ?? "",
          rating: l.rating ?? null,
          confidence: l.confidence_score ?? null,
        },
        geometry: {
          type: "Point" as const,
          coordinates: [l.lng, l.lat] as [number, number],
        },
      })),
    }),
    [locations]
  );

  /** Eénmalige init zodra style er is */
  useEffect(() => {
    if (initialized.current) return;

    const init = () => {
      if (initialized.current) return;

      // Zorg dat de style écht geladen is. Zo niet: wacht nog één keer.
      if (!map.isStyleLoaded?.()) {
        // Sommige styles emitten 'style.load' nadat 'load' al geweest is (bv. style switch).
        map.once("style.load", init as any);
        return;
      }

      // Source toevoegen (1x)
      if (!map.getSource(SRC_ID)) {
        map.addSource(SRC_ID, {
          type: "geojson",
          data: data as any,
          cluster: true,
          clusterMaxZoom: 14,
          clusterRadius: 50,
        });
      }

      // Cluster laag
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

      // Cluster count laag
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

      // Punten laag (on-clustered)
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

      // Highlight laag
      if (!map.getLayer(L_HI)) {
        map.addLayer({
          id: L_HI,
          type: "circle",
          source: SRC_ID,
          filter: ["all", ["!", ["has", "point_count"]], ["==", ["get", "id"], -1]],
          paint: {
            "circle-color": "#22c55e",
            "circle-radius": 10,
            "circle-stroke-color": "#14532d",
            "circle-stroke-width": 2,
          },
        });
      }

      // Interactie handlers (1x, types bewust generiek gehouden i.v.m. mapbox-gl typings)
      const onClusterClick = (e: any) => {
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

      const onPointClick = (e: any) => {
        const feats = map.queryRenderedFeatures(e.point, { layers: [L_POINT] }) as
          | MapboxGeoJSONFeature[]
          | undefined;
        const id = Number(feats?.[0]?.properties?.id);
        if (Number.isFinite(id)) {
          onSelect?.(id);
        }
      };

      const onEnter = () => {
        try {
          map.getCanvas().style.cursor = "pointer";
        } catch {}
      };
      const onLeave = () => {
        try {
          map.getCanvas().style.cursor = "";
        } catch {}
      };

      // Register event handlers after a small delay to ensure layers are fully rendered
      setTimeout(() => {
        map.on("click", L_CLUSTER, onClusterClick as any);
        map.on("mouseenter", L_CLUSTER, onEnter as any);
        map.on("mouseleave", L_CLUSTER, onLeave as any);
        map.on("click", L_POINT, onPointClick as any);
        map.on("mouseenter", L_POINT, onEnter as any);
        map.on("mouseleave", L_POINT, onLeave as any);
      }, 100);

      initialized.current = true;

      // Cleanup handlers bij unmount
      return () => {
        try {
          map.off("click", L_CLUSTER, onClusterClick as any);
          map.off("mouseenter", L_CLUSTER, onEnter as any);
          map.off("mouseleave", L_CLUSTER, onLeave as any);
          map.off("click", L_POINT, onPointClick as any);
          map.off("mouseenter", L_POINT, onEnter as any);
          map.off("mouseleave", L_POINT, onLeave as any);
        } catch {}
      };
    };

    // Wachten tot er überhaupt een style is (voorkomt de “no style added” warning)
    if (!hasStyleObject(map)) {
      map.once("load", init as any);
      return () => {
        try {
          map.off("load", init as any);
        } catch {}
      };
    }

    // Style-object bestaat al → init proberen
    const cleanup = init();
    return cleanup;
  }, [map, data, onSelect]);

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

    const id = Number.isFinite(selectedId) ? (selectedId as number) : -1;
    try {
      map.setFilter(L_HI, ["all", ["!", ["has", "point_count"]], ["==", ["get", "id"], id]]);
    } catch {}
  }, [map, selectedId]);

  return null;
}

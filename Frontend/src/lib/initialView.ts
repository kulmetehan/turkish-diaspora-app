import type { Map as MapboxMap } from "mapbox-gl";
import { CLUSTER_CONFIG } from "@/lib/config";
import { isMobile } from "@/lib/utils";
import { MarkerLayerIds } from "@/components/markerLayerUtils";
import { distanceKm, MAX_NEARBY_DISTANCE_KM, NEARBY_STICKY_DISTANCE_KM } from "@/lib/geo";

export interface InitialViewTarget {
  center: [number, number];
  zoom: number;
  clusterId?: number; // If set, indicates this is a cluster that needs expansion
}

/**
 * Computes an initial map view that guarantees at least one unclustered marker is visible.
 * 
 * Uses the initial center as an anchor to find the nearest feature (marker or cluster).
 * Determines coverage based on distance to nearest feature:
 * - If nearest feature is within MAX_NEARBY_DISTANCE_KM: returns view centered on that feature
 * - If nearest feature is outside MAX_NEARBY_DISTANCE_KM or no features exist: returns fallback view (Rotterdam)
 * 
 * If the nearest feature is a cluster, returns a view with clusterId set so the caller
 * can use getClusterExpansionZoom to determine the exact zoom level.
 * If it's already a point marker, uses the cluster max zoom to ensure it remains unclustered.
 * 
 * @param args Configuration for computing the initial view
 * @param args.initialCenter The initial center (from geolocation or fallback) to search from
 * @param args.fallbackCenter The fallback center (Rotterdam) to use when outside coverage
 * @returns Initial view target with center and zoom, or null if computation fails
 */
export function computeInitialUnclusteredView(args: {
  map: MapboxMap;
  isMobile: boolean;
  initialCenter: [number, number];
  fallbackCenter: [number, number];
  fallbackZoom: number;
}): InitialViewTarget | null {
  const { map, isMobile: mobile, initialCenter, fallbackCenter, fallbackZoom } = args;

  try {
    // Wait for style and source to be loaded
    const styleLoaded = typeof map.isStyleLoaded === "function" ? map.isStyleLoaded() : true;
    if (!styleLoaded) {
      return null;
    }

    const source = map.getSource(MarkerLayerIds.SRC_ID);
    if (!source || source.type !== "geojson") {
      return null;
    }

    // Use querySourceFeatures to get features at current zoom
    const geojsonSource = source as any;
    if (typeof geojsonSource.querySourceFeatures !== "function") {
      return null;
    }

    // Query all features in the source
    const features = geojsonSource.querySourceFeatures();
    if (!Array.isArray(features) || features.length === 0) {
      // Empty dataset - return null to keep fallback zoom
      return null;
    }

    // Find nearest feature to the initial center (could be geolocation or fallback)
    const [initialLng, initialLat] = initialCenter;
    let nearestFeature: any = null;
    let minDistanceKm = Infinity;

    for (const feature of features) {
      if (!feature.geometry || feature.geometry.type !== "Point") continue;
      const [lng, lat] = feature.geometry.coordinates;
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;

      // Calculate distance in kilometers using haversine formula
      const distance = distanceKm(initialLat, initialLng, lat, lng);

      if (distance < minDistanceKm) {
        minDistanceKm = distance;
        nearestFeature = feature;
      }
    }

    // Check if user is within coverage based on distance to nearest feature
    if (!nearestFeature || minDistanceKm > MAX_NEARBY_DISTANCE_KM) {
      // Outside coverage or no features - return fallback view (Rotterdam)
      // Find nearest feature to Rotterdam to ensure at least one unclustered marker is visible
      const [fallbackLng, fallbackLat] = fallbackCenter;
      let nearestToFallback: any = null;
      let minDistanceToFallbackKm = Infinity;

      for (const feature of features) {
        if (!feature.geometry || feature.geometry.type !== "Point") continue;
        const [lng, lat] = feature.geometry.coordinates;
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) continue;

        const distance = distanceKm(fallbackLat, fallbackLng, lat, lng);
        if (distance < minDistanceToFallbackKm) {
          minDistanceToFallbackKm = distance;
          nearestToFallback = feature;
        }
      }

      if (!nearestToFallback) {
        // No features at all - return null to keep fallback zoom
        if (import.meta.env.DEV) {
          console.debug("[InitialUnclusteredView]", {
            initialCenter,
            fallbackCenter,
            nearestFeatureDistanceKm: null,
            usedFallback: false,
            reason: "No features available",
          });
        }
        return null;
      }

      // Return view centered on nearest feature to Rotterdam
      const [nearestLng, nearestLat] = nearestToFallback.geometry.coordinates;
      const clusterMaxZoom = mobile ? CLUSTER_CONFIG.MOBILE_MAX_ZOOM : CLUSTER_CONFIG.MAX_ZOOM;
      const isCluster = Boolean(nearestToFallback.properties?.cluster_id !== undefined);
      const clusterId = nearestToFallback.properties?.cluster_id;

      const result = isCluster && typeof clusterId === "number"
        ? {
            center: [nearestLng, nearestLat] as [number, number],
            zoom: clusterMaxZoom,
            clusterId,
          }
        : {
            center: [nearestLng, nearestLat] as [number, number],
            zoom: Math.max(clusterMaxZoom - 1, fallbackZoom),
          };

      if (import.meta.env.DEV) {
        console.debug("[InitialUnclusteredView]", {
          initialCenter,
          fallbackCenter,
          nearestFeatureDistanceKm: minDistanceKm,
          usedFallback: true,
          reason: `User outside coverage (${minDistanceKm.toFixed(1)}km > ${MAX_NEARBY_DISTANCE_KM}km)`,
        });
      }

      return result;
    }

    // Inside coverage - determine if we should be "sticky" to user or center on feature
    const [nearestLng, nearestLat] = nearestFeature.geometry.coordinates;
    const clusterMaxZoom = mobile ? CLUSTER_CONFIG.MOBILE_MAX_ZOOM : CLUSTER_CONFIG.MAX_ZOOM;

    // Check if nearest feature is a cluster
    const isCluster = Boolean(nearestFeature.properties?.cluster_id !== undefined);
    const clusterId = nearestFeature.properties?.cluster_id;

    // If user is very close to the nearest feature (within sticky distance), keep camera user-centric
    // Otherwise, center on the feature for better marker visibility
    const isSticky = minDistanceKm <= NEARBY_STICKY_DISTANCE_KM;
    const targetCenter: [number, number] = isSticky
      ? initialCenter // Keep user's location as center
      : [nearestLng, nearestLat]; // Center on nearest feature

    if (isCluster && typeof clusterId === "number") {
      // It's a cluster - return view with clusterId so caller can expand it
      // Use cluster max zoom as initial zoom, caller will expand if needed
      const result = {
        center: targetCenter,
        zoom: clusterMaxZoom,
        clusterId,
      };

      if (import.meta.env.DEV) {
        console.debug("[InitialUnclusteredView]", {
          initialCenter,
          fallbackCenter,
          nearestFeatureDistanceKm: minDistanceKm,
          usedFallback: false,
          isSticky,
          reason: `Cluster found, ${isSticky ? "sticky to user" : "centered on cluster"}`,
        });
      }

      return result;
    } else {
      // It's already a point marker - use cluster max zoom to ensure it stays unclustered
      // Use slightly lower zoom for better visibility (not too zoomed in)
      const targetZoom = Math.max(clusterMaxZoom - 1, fallbackZoom);
      const result = {
        center: targetCenter,
        zoom: targetZoom,
      };

      if (import.meta.env.DEV) {
        console.debug("[InitialUnclusteredView]", {
          initialCenter,
          fallbackCenter,
          nearestFeatureDistanceKm: minDistanceKm,
          usedFallback: false,
          isSticky,
          reason: `Point marker found, ${isSticky ? "sticky to user" : "centered on marker"}`,
        });
      }

      return result;
    }
  } catch {
    return null;
  }
}


// Frontend/src/lib/map/mapbox.ts
import mapboxgl, { Map } from "mapbox-gl";
import { CONFIG } from "@/lib/config";

/**
 * Safely check if a layer exists on the map, guarding against empty/undefined layer IDs
 * to prevent "IDs can't be empty" errors from Mapbox GL JS.
 */
export function safeHasLayer(
  map: Map | null | undefined,
  id: string | undefined | null
): boolean {
  if (!map) return false;
  // Guard against empty or undefined layer IDs to prevent "IDs can't be empty" errors
  if (!id || typeof id !== "string" || id.trim() === "") return false;
  try {
    return Boolean(map.getLayer(id));
  } catch {
    return false;
  }
}

export function initMap(container: HTMLElement): Map {
  mapboxgl.accessToken = CONFIG.MAPBOX_TOKEN;
  const map = new mapboxgl.Map({
    container,
    style: CONFIG.MAPBOX_STYLE,
    center: [CONFIG.MAP_DEFAULT.lng, CONFIG.MAP_DEFAULT.lat],
    zoom: CONFIG.MAP_DEFAULT.zoom,
    minZoom: CONFIG.MAP_MIN_ZOOM,
    maxZoom: CONFIG.MAP_MAX_ZOOM,
    dragRotate: false,
    attributionControl: true,
    projection: "mercator",
    locale: { "NavigationControl.ZoomIn": "Zoom in", "NavigationControl.ZoomOut": "Zoom out" }
  });

  map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-right");
  map.addControl(new mapboxgl.FullscreenControl(), "bottom-right");
  map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");

  return map;
}

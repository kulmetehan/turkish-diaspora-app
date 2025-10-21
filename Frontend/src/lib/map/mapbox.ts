// Frontend/src/lib/map/mapbox.ts
import mapboxgl, { Map } from "mapbox-gl";
import { CONFIG } from "@/lib/config";

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

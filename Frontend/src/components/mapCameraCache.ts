import type { LngLatLike, Map as MapboxMap } from "mapbox-gl";

type CameraState = {
  center: LngLatLike;
  zoom: number;
  bearing: number;
  pitch: number;
  padding?: mapboxgl.PaddingOptions;
};

let cachedCamera: CameraState | null = null;

export function restoreCamera(map: MapboxMap, focusActive: boolean): void {
  if (!cachedCamera || focusActive) return;
  try {
    map.jumpTo({
      center: cachedCamera.center,
      zoom: cachedCamera.zoom,
      bearing: cachedCamera.bearing,
      pitch: cachedCamera.pitch,
      padding: cachedCamera.padding,
    });
  } catch {
    /* ignore */
  }
}

export function storeCamera(map: MapboxMap): void {
  try {
    cachedCamera = {
      center: map.getCenter().toArray(),
      zoom: map.getZoom(),
      bearing: map.getBearing(),
      pitch: map.getPitch(),
      padding: map.getPadding?.(),
    };
  } catch {
    /* ignore */
  }
}

export function clearCamera(): void {
  cachedCamera = null;
}



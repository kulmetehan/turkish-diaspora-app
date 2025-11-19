export const NL_CENTER = { lat: 52.1326, lng: 5.2913 };
export const NL_ZOOM = 7;

/**
 * Rotterdam bounding box based on Infra/config/cities.yml and Docs/city-grid.md
 * Used to determine if a geolocated position is within coverage area
 */
const ROTTERDAM_BBOX = {
  lat_min: 51.85,
  lat_max: 51.98,
  lng_min: 4.35,
  lng_max: 4.55,
} as const;

/**
 * Checks if the given coordinates are within Rotterdam's coverage bounds.
 * Used to determine if geolocation should be used or fallback to Rotterdam default.
 */
export function isWithinRotterdamBounds(lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return false;
  }
  return (
    lat >= ROTTERDAM_BBOX.lat_min &&
    lat <= ROTTERDAM_BBOX.lat_max &&
    lng >= ROTTERDAM_BBOX.lng_min &&
    lng <= ROTTERDAM_BBOX.lng_max
  );
}

export function haversineMeters(a: {lat:number; lng:number}, b: {lat:number; lng:number}): number {
  const R = 6371000; // meters
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const la1 = toRad(a.lat);
  const la2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(la1) * Math.cos(la2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/**
 * Calculates the distance between two coordinates in kilometers using the haversine formula.
 * 
 * @param lat1 Latitude of first point
 * @param lng1 Longitude of first point
 * @param lat2 Latitude of second point
 * @param lng2 Longitude of second point
 * @returns Distance in kilometers
 */
export function distanceKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number
): number {
  if (!Number.isFinite(lat1) || !Number.isFinite(lng1) || !Number.isFinite(lat2) || !Number.isFinite(lng2)) {
    return Infinity;
  }
  const meters = haversineMeters({ lat: lat1, lng: lng1 }, { lat: lat2, lng: lng2 });
  return meters / 1000; // Convert meters to kilometers
}

/**
 * Maximum distance (in kilometers) to consider a location as "nearby" for coverage detection.
 * Used by the initial view heuristic to determine if the user is within coverage area.
 */
export const MAX_NEARBY_DISTANCE_KM = 30;

/**
 * Distance (in kilometers) within which the camera should stay "sticky" to the user's location.
 * If the nearest feature is within this distance, the view will be user-centric rather than
 * aggressively recentering on the feature.
 */
export const NEARBY_STICKY_DISTANCE_KM = 10;

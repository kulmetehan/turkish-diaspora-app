// Frontend/src/types/location.ts

// Keep this file *purely types* to play nicely with `"verbatimModuleSyntax": true`.
// Do not import runtime modules here.

/**
 * Optional high-level state for a location in our pipeline.
 * Kept as string to stay compatible with the backend values.
 */
export type LocationState = string;

/**
 * Core Location shape used across MapView, List & Filters.
 * Fields marked as optional are not guaranteed by every source.
 */
export interface Location {
  /** Stable id from our DB (stringified if it was bigint). */
  id: string;

  /** Optional Google place_id (if present in our data). */
  place_id?: string;

  /** Human readable basics */
  name: string;
  address?: string;

  /** Geo */
  lat: number;
  lng: number;

  /** Classification */
  category?: string;

  /** Ratings (Google-style) */
  rating?: number | null;
  user_ratings_total?: number | null;

  /** Pipeline / verification */
  state?: LocationState;
  last_verified_at?: string | null; // ISO datetime if available

  /**
   * Client-side computed helper (never persisted by the API).
   * Filled by the frontend based on user position.
   */
  distanceKm?: number;
}

/**
 * Convenience type for arrays coming from the API.
 */
export type LocationList = Location[];

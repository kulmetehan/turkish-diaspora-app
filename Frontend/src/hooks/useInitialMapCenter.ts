import { useEffect, useState, useRef } from "react";
import { CONFIG } from "@/lib/config";

type InitialCenterSource = "geolocation" | "fallback_city";
type InitialCenterStatus = "idle" | "resolving" | "resolved";

export interface UseInitialMapCenterResult {
  initialCenter: { lng: number; lat: number };
  initialZoom: number;
  source: InitialCenterSource;
  status: InitialCenterStatus;
  error?: string;
}

const SESSION_STORAGE_KEY = "tda_initialView_geolocation_requested";

/**
 * Determines the initial map center and zoom based on geolocation permissions.
 * 
 * Hook Contract:
 * - Initial state (`status: "idle"`) contains Rotterdam as a placeholder. MapView should treat
 *   this as a temporary value and wait for `status === "resolved"` before making final camera decisions.
 * - When `status === "resolved"` and `source === "geolocation"`, `initialCenter` is definitely
 *   the user's geolocation coordinates (regardless of whether they're near coverage).
 * - When `status === "resolved"` and `source === "fallback_city"`, `initialCenter` is Rotterdam (MAP_DEFAULT).
 * 
 * Behavior:
 * - If geolocation permission is already granted, requests position and uses it (regardless of location)
 * - If permission state is "prompt", attempts geolocation once per session (triggers browser prompt)
 * - If permission is denied or geolocation fails, falls back to Rotterdam (MAP_DEFAULT)
 * - Coverage detection (whether user is near any locations) is handled by the initial view heuristic
 */
export function useInitialMapCenter(): UseInitialMapCenterResult {
  const hasRequestedGeolocationRef = useRef(false);
  const [result, setResult] = useState<UseInitialMapCenterResult>(() => {
    // Initial state: use Rotterdam fallback immediately
    return {
      initialCenter: {
        lng: CONFIG.MAP_DEFAULT.lng,
        lat: CONFIG.MAP_DEFAULT.lat,
      },
      initialZoom: CONFIG.MAP_DEFAULT.zoom,
      source: "fallback_city",
      status: "idle",
    };
  });

  useEffect(() => {
    let cancelled = false;

    // Check if we've already requested geolocation in this session
    const hasRequestedInSession = typeof window !== "undefined" && 
      sessionStorage.getItem(SESSION_STORAGE_KEY) === "true";
    
    if (hasRequestedInSession) {
      hasRequestedGeolocationRef.current = true;
    }

    // Check if Permissions API is available
    const checkPermission = async () => {
      if (cancelled) return;

      // If geolocation API is not available, use fallback immediately
      if (!("geolocation" in navigator) || !navigator.geolocation) {
        setResult((prev) => ({
          ...prev,
          status: "resolved",
        }));
        return;
      }

      // Check permission status using Permissions API if available
      let permissionState: PermissionState | null = null;
      try {
        const permission = await navigator.permissions.query({ name: "geolocation" as PermissionName });
        permissionState = permission.state;
      } catch {
        // Permissions API not supported or query failed
        // Treat as "prompt" - we'll try once if not already requested
      }

      const requestGeolocation = () => {
        if (cancelled) return;
        
        // Mark as requested in session storage
        if (typeof window !== "undefined") {
          sessionStorage.setItem(SESSION_STORAGE_KEY, "true");
        }
        hasRequestedGeolocationRef.current = true;

        setResult((prev) => ({
          ...prev,
          status: "resolving",
        }));

        navigator.geolocation.getCurrentPosition(
          (position) => {
            if (cancelled) return;

            const { latitude, longitude } = position.coords;
            if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
              // Invalid coordinates, fallback to Rotterdam
              setResult({
                initialCenter: {
                  lng: CONFIG.MAP_DEFAULT.lng,
                  lat: CONFIG.MAP_DEFAULT.lat,
                },
                initialZoom: CONFIG.MAP_DEFAULT.zoom,
                source: "fallback_city",
                status: "resolved",
                error: "Invalid geolocation coordinates",
              });
              if (import.meta.env.DEV) {
                console.info("[InitialMapCenter]", {
                  source: "fallback_city",
                  center: { lng: CONFIG.MAP_DEFAULT.lng, lat: CONFIG.MAP_DEFAULT.lat },
                  zoom: CONFIG.MAP_DEFAULT.zoom,
                  permissionState: permissionState ?? "unknown",
                  reason: "Invalid coordinates",
                });
              }
              return;
            }

            // Always use geolocation coordinates when permission is granted and position is valid
            // Coverage detection is handled by the initial view heuristic based on distance to nearest feature
            setResult({
              initialCenter: {
                lng: longitude,
                lat: latitude,
              },
              initialZoom: CONFIG.MAP_MY_LOCATION_ZOOM ?? 14,
              source: "geolocation",
              status: "resolved",
            });
            
            if (import.meta.env.DEV) {
              console.info("[InitialMapCenter]", {
                source: "geolocation",
                center: { lng: longitude, lat: latitude },
                zoom: CONFIG.MAP_MY_LOCATION_ZOOM ?? 14,
                permissionState: permissionState ?? "unknown",
              });
            }
          },
          (error) => {
            if (cancelled) return;

            // On error, fallback to Rotterdam
            let errorMessage = "Geolocation failed";
            if (error.code === error.PERMISSION_DENIED) {
              errorMessage = "Permission denied";
            } else if (error.code === error.POSITION_UNAVAILABLE) {
              errorMessage = "Position unavailable";
            } else if (error.code === error.TIMEOUT) {
              errorMessage = "Geolocation timeout";
            }

            setResult({
              initialCenter: {
                lng: CONFIG.MAP_DEFAULT.lng,
                lat: CONFIG.MAP_DEFAULT.lat,
              },
              initialZoom: CONFIG.MAP_DEFAULT.zoom,
              source: "fallback_city",
              status: "resolved",
              error: errorMessage,
            });
            
            if (import.meta.env.DEV) {
              console.info("[InitialMapCenter]", {
                source: "fallback_city",
                center: { lng: CONFIG.MAP_DEFAULT.lng, lat: CONFIG.MAP_DEFAULT.lat },
                zoom: CONFIG.MAP_DEFAULT.zoom,
                permissionState: permissionState ?? "unknown",
                error: errorMessage,
              });
            }
          },
          {
            enableHighAccuracy: false,
            timeout: 8000,
            maximumAge: 60_000,
          }
        );
      };

      if (permissionState === "granted") {
        // Permission already granted - request geolocation
        requestGeolocation();
      } else if (permissionState === "prompt" && !hasRequestedGeolocationRef.current) {
        // Permission is in prompt state and we haven't requested yet - try once
        requestGeolocation();
      } else if (permissionState === "denied") {
        // Permission denied - use Rotterdam fallback immediately
        setResult((prev) => ({
          ...prev,
          status: "resolved",
        }));
        if (import.meta.env.DEV) {
          console.info("[InitialMapCenter]", {
            source: "fallback_city",
            center: { lng: CONFIG.MAP_DEFAULT.lng, lat: CONFIG.MAP_DEFAULT.lat },
            zoom: CONFIG.MAP_DEFAULT.zoom,
            permissionState: "denied",
            reason: "Permission denied",
          });
        }
      } else if (permissionState === null && !hasRequestedGeolocationRef.current) {
        // Permissions API not available - treat as prompt and try once
        requestGeolocation();
      } else {
        // Already requested or unknown state - use Rotterdam fallback
        setResult((prev) => ({
          ...prev,
          status: "resolved",
        }));
        if (import.meta.env.DEV) {
          console.info("[InitialMapCenter]", {
            source: "fallback_city",
            center: { lng: CONFIG.MAP_DEFAULT.lng, lat: CONFIG.MAP_DEFAULT.lat },
            zoom: CONFIG.MAP_DEFAULT.zoom,
            permissionState: permissionState ?? "unknown",
            reason: "Already requested or unknown state",
          });
        }
      }
    };

    void checkPermission();

    return () => {
      cancelled = true;
    };
  }, []);

  return result;
}


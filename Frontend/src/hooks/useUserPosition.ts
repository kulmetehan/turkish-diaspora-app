import { useEffect, useState } from "react";

type Status = "idle" | "granted" | "denied" | "prompt" | "error";

export interface UseUserPositionOptions {
  /**
   * If true, automatically request geolocation on mount.
   * If false, only check permission status without requesting position.
   * @default false
   */
  autoRequest?: boolean;
  /**
   * Timeout in milliseconds for geolocation request.
   * @default 8000
   */
  timeoutMs?: number;
}

export function useUserPosition(options: UseUserPositionOptions | number = {}) {
  // Support legacy number parameter for timeoutMs
  const opts: UseUserPositionOptions =
    typeof options === "number" ? { timeoutMs: options } : options;
  const { autoRequest = false, timeoutMs = 8000 } = opts;

  const [status, setStatus] = useState<Status>("idle");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setStatus("error");
      setError("Geolocatie niet beschikbaar.");
      return;
    }

    let cancelled = false;

    // Check permission status if Permissions API is available
    const checkPermission = async () => {
      try {
        const permission = await navigator.permissions.query({ name: "geolocation" as PermissionName });
        if (cancelled) return;

        if (permission.state === "denied") {
          setStatus("denied");
          setError("Geolocatie toegang geweigerd.");
          return;
        }

        if (permission.state === "granted" && autoRequest) {
          setStatus("prompt");
          requestPosition();
        } else if (permission.state === "prompt") {
          setStatus("prompt");
          if (autoRequest) {
            requestPosition();
          }
        } else {
          setStatus(permission.state as Status);
        }
      } catch {
        // Permissions API not supported, fall through to direct request if autoRequest
        if (autoRequest) {
          setStatus("prompt");
          requestPosition();
        } else {
          setStatus("idle");
        }
      }
    };

    const requestPosition = () => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          if (cancelled) return;
          setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
          setStatus("granted");
        },
        (err) => {
          if (cancelled) return;
          setError(err.message || "Geolocatie mislukt.");
          setStatus(err.code === err.PERMISSION_DENIED ? "denied" : "error");
        },
        {
          enableHighAccuracy: false,
          timeout: timeoutMs,
          maximumAge: 60_000,
        }
      );
    };

    void checkPermission();

    return () => {
      cancelled = true;
    };
  }, [autoRequest, timeoutMs]);

  return { status, coords, error };
}

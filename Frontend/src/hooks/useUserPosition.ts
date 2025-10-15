import { useEffect, useState } from "react";

type Status = "idle" | "granted" | "denied" | "prompt" | "error";

export function useUserPosition(timeoutMs = 8000) {
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
    setStatus("prompt");

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

    return () => {
      cancelled = true;
    };
  }, [timeoutMs]);

  return { status, coords, error };
}

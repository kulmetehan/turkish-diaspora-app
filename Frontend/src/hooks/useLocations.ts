// src/hooks/useLocations.ts
import { useEffect, useState } from "react";
import { fetchLocations, type Location } from "@/lib/api/location";

export function useLocations() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchLocations()
      .then((data) => {
        if (active) setLocations(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { locations, isLoading, error };
}

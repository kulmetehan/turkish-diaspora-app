// Frontend/src/components/trending/DiasporaPulseLite.tsx
import { useEffect, useState } from "react";
import { TrendingLocationCard } from "./TrendingLocationCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { getTrendingLocations, type TrendingLocation } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/ui/cn";

interface DiasporaPulseLiteProps {
  className?: string;
}

// Available cities (can be extended)
const AVAILABLE_CITIES = [
  { key: "rotterdam", label: "Rotterdam" },
  { key: "den_haag", label: "Den Haag" },
  { key: "amsterdam", label: "Amsterdam" },
  { key: "utrecht", label: "Utrecht" },
];

export function DiasporaPulseLite({ className }: DiasporaPulseLiteProps) {
  const [locations, setLocations] = useState<TrendingLocation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>("all");
  const [window, setWindow] = useState<string>("24h");

  useEffect(() => {
    loadTrending();
  }, [selectedCity, window]);

  const loadTrending = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getTrendingLocations(
        selectedCity === "all" ? undefined : selectedCity,
        undefined,
        window,
        20
      );
      setLocations(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon trending locaties niet laden";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && locations.length === 0) {
    return (
      <div className={cn("space-y-4", className)}>
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-24 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error && locations.length === 0) {
    return (
      <div className={cn("rounded-xl border border-border/80 bg-card p-6 text-center shadow-soft", className)}>
        <p className="text-foreground">{error}</p>
        <Button
          size="sm"
          className="mt-4"
          onClick={loadTrending}
          variant="outline"
        >
          Opnieuw proberen
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Select value={selectedCity} onValueChange={setSelectedCity}>
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="Alle steden" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Alle steden</SelectItem>
            {AVAILABLE_CITIES.map((city) => (
              <SelectItem key={city.key} value={city.key}>
                {city.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={window} onValueChange={setWindow}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="5m">Laatste 5 min</SelectItem>
            <SelectItem value="1h">Laatste uur</SelectItem>
            <SelectItem value="24h">Laatste 24 uur</SelectItem>
            <SelectItem value="7d">Laatste week</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Trending Locations Grid */}
      {locations.length === 0 ? (
        <div className="rounded-xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-soft">
          <p>Er zijn nog geen trending locaties in deze periode.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {locations.map((location) => (
            <TrendingLocationCard key={location.location_id} location={location} />
          ))}
        </div>
      )}
    </div>
  );
}



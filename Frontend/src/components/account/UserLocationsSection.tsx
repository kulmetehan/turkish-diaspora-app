import { useEffect, useState } from "react";
import { getMyLocations, type MyLocation } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { getCategoryIcon } from "@/lib/map/marker-icons";
import { useUserAuth } from "@/hooks/useUserAuth";

interface UserLocationsSectionProps {
  className?: string;
}

export function UserLocationsSection({ className }: UserLocationsSectionProps) {
  const [locations, setLocations] = useState<MyLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useUserAuth();

  useEffect(() => {
    // Only fetch if user is authenticated and auth check is complete
    if (authLoading) {
      return;
    }

    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    async function fetchLocations() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMyLocations();
        setLocations(data || []);
      } catch (err) {
        setError("Failed to load locations");
      } finally {
        setLoading(false);
      }
    }

    fetchLocations();
  }, [isAuthenticated, authLoading]);

  // Don't render if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  if (loading || authLoading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Locaties
          </h2>
          <p className="text-sm text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Locaties
          </h2>
          <p className="text-sm text-muted-foreground">
            Kon locaties niet laden. Probeer het later opnieuw.
          </p>
        </div>
      </div>
    );
  }

  // Always show the section, even if empty (so user knows the feature exists)
  // Only hide if there's an error and no locations
  if (!locations || locations.length === 0) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Locaties
          </h2>
          <p className="text-sm text-muted-foreground">
            Je hebt nog geen locaties geclaimd.
          </p>
        </div>
      </div>
    );
  }

  const handleLocationClick = (locationId: number) => {
    navigate(`/locations/${locationId}`);
  };

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-3">
        <h2 className="text-lg font-gilroy font-medium text-foreground">
          Locaties
        </h2>
        <div className="space-y-2">
          {locations.map((location) => {
            const CategoryIcon = location.category
              ? getCategoryIcon(location.category)
              : null;
            
            return (
              <button
                key={location.location_id}
                type="button"
                onClick={() => handleLocationClick(location.location_id)}
                className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-surface-muted/70 transition-colors text-left group"
              >
                {CategoryIcon ? (
                  <CategoryIcon className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                ) : (
                  <Icon name="MapPin" className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-gilroy font-medium text-foreground group-hover:text-primary transition-colors">
                    {location.location_name || "Onbekende locatie"}
                  </p>
                  {location.address && (
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                      {location.address}
                    </p>
                  )}
                  {location.category && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {location.category}
                    </p>
                  )}
                </div>
                <Icon
                  name="ChevronRight"
                  className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 mt-1"
                />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}


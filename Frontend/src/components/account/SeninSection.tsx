import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/ui/cn";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { getMyLocations, type MyLocation } from "@/lib/api";
import { getMyRoles, type UserRolesResponse } from "@/lib/api";

interface SeninSectionProps {
  className?: string;
}

export function SeninSection({ className }: SeninSectionProps) {
  const navigate = useNavigate();
  const [locations, setLocations] = useState<MyLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOwner, setIsOwner] = useState(false);

  useEffect(() => {
    async function checkOwnerAndLoadLocations() {
      try {
        // Check if user has location_owner role
        const roles = await getMyRoles();
        const hasOwnerRole = roles.primary_role === "location_owner" || roles.secondary_role === "location_owner";
        setIsOwner(hasOwnerRole);

        if (hasOwnerRole) {
          // Load owned locations
          const data = await getMyLocations();
          setLocations(data);
        }
      } catch (err) {
        console.error("Failed to load locations:", err);
      } finally {
        setLoading(false);
      }
    }

    checkOwnerAndLoadLocations();
  }, []);

  // Don't show section if user is not a location owner
  if (!isOwner || loading) {
    return null;
  }

  // Don't show section if no locations
  if (locations.length === 0) {
    return null;
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("nl-NL", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Senin
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Jouw geclaimde locaties
          </p>
        </div>

        <div className="space-y-3">
          {locations.map((location) => (
            <div
              key={location.location_id}
              className="flex items-start justify-between p-4 bg-background rounded-lg border border-border hover:bg-accent transition-colors cursor-pointer"
              onClick={() => navigate(`/locations/${location.location_id}`)}
            >
              <div className="flex-1 space-y-1">
                <h3 className="font-semibold text-foreground">
                  {location.location_name || `Locatie ${location.location_id}`}
                </h3>
                {location.category && (
                  <p className="text-sm text-muted-foreground">
                    {location.category}
                  </p>
                )}
                {location.claimed_at && (
                  <p className="text-xs text-muted-foreground">
                    Geclaimed op {formatDate(location.claimed_at)}
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/locations/${location.location_id}`);
                }}
              >
                <Icon name="ChevronRight" sizeRem={1} />
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


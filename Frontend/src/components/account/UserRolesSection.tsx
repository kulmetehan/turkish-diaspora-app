import MekaninSahibiAvatar from "@/assets/mekaninsahibi.png";
import { MascotteAvatar } from "@/components/onboarding/MascotteAvatar";
import { useMascotteFeedback } from "@/hooks/useMascotteFeedback";
import { getMyRoles, type UserRolesResponse } from "@/lib/api";
import { roleDisplayName } from "@/lib/roleDisplay";
import { cn } from "@/lib/ui/cn";
import { useEffect, useRef, useState } from "react";

interface UserRolesSectionProps {
  className?: string;
}

export function UserRolesSection({ className }: UserRolesSectionProps) {
  const [roles, setRoles] = useState<UserRolesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { showMascotteFeedback } = useMascotteFeedback();
  const previousRolesRef = useRef<{ primary?: string; secondary?: string } | null>(null);
  const fetchingRef = useRef(false);

  useEffect(() => {
    async function fetchRoles() {
      // Prevent concurrent fetches
      if (fetchingRef.current) {
        return;
      }

      try {
        fetchingRef.current = true;
        setLoading(true);
        setError(null);
        const data = await getMyRoles();

        // Check for role changes
        if (previousRolesRef.current) {
          const prev = previousRolesRef.current;
          const current = {
            primary: data.primary_role || undefined,
            secondary: data.secondary_role || undefined,
          };

          // Detect if primary or secondary role changed
          if (
            prev.primary !== current.primary ||
            prev.secondary !== current.secondary
          ) {
            // Only trigger if we had previous roles (not first load)
            if (prev.primary || prev.secondary) {
              showMascotteFeedback("role_changed");
            }
          }
        }

        // Update previous roles
        previousRolesRef.current = {
          primary: data.primary_role || undefined,
          secondary: data.secondary_role || undefined,
        };

        setRoles(data);
      } catch (err) {
        console.error("Failed to fetch roles:", err);
        setError("Failed to load roles");
      } finally {
        setLoading(false);
        fetchingRef.current = false;
      }
    }

    fetchRoles();

    // Poll for role changes every 5 minutes (optional enhancement)
    const intervalId = setInterval(fetchRoles, 5 * 60 * 1000);

    return () => {
      clearInterval(intervalId);
    };
  }, [showMascotteFeedback]);

  if (loading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Titels
          </h2>
          <p className="text-sm text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (error || !roles) {
    return null; // Don't show section if there's an error or no roles
  }

  const rolesList: string[] = [];
  if (roles.primary_role) {
    rolesList.push(roleDisplayName(roles.primary_role));
  }
  if (roles.secondary_role) {
    rolesList.push(roleDisplayName(roles.secondary_role));
  }

  if (rolesList.length === 0) {
    return null; // Don't show section if no roles
  }

  const renderRoleAvatar = (role: string) => {
    if (role === "location_owner") {
      return (
        <img
          src={MekaninSahibiAvatar}
          alt="Mekanın sahibi"
          className={cn("object-contain", "h-16 w-16")}
        />
      );
    }
    return <MascotteAvatar size="sm" />;
  };

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-3">
        <h2 className="text-lg font-gilroy font-medium text-foreground">
          Titels
        </h2>
        <div className="flex items-center gap-3 flex-wrap">
          {roles.primary_role && (
            <div className="flex items-center gap-2">
              {renderRoleAvatar(roles.primary_role)}
              <span className="text-sm text-muted-foreground">
                {roleDisplayName(roles.primary_role)}
              </span>
            </div>
          )}
          {roles.secondary_role && (
            <div className="flex items-center gap-2">
              {renderRoleAvatar(roles.secondary_role)}
              <span className="text-sm text-muted-foreground">
                {roleDisplayName(roles.secondary_role)}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


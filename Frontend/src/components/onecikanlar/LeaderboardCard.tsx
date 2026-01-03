// Frontend/src/components/onecikanlar/LeaderboardCard.tsx
import mekaninsahibiIcon from "@/assets/mekaninsahibi.png";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { roleDisplayName } from "@/lib/roleDisplay";
import type { LeaderboardCard as LeaderboardCardType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

/**
 * Get role image for a given role key.
 * Returns the image path or null if no image is available.
 */
function getRoleImage(roleKey: string | null | undefined): string | null {
  if (!roleKey) return null;

  const roleImages: Record<string, string> = {
    location_owner: mekaninsahibiIcon,
    // Add more role images here as they become available
  };

  return roleImages[roleKey] || null;
}

/**
 * Get user initials from name.
 */
function getInitials(name: string | null | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }
  return name.charAt(0).toUpperCase();
}

export interface LeaderboardCardProps {
  card: LeaderboardCardType;
  onUserClick?: (userId: string) => void;
  className?: string;
}

export function LeaderboardCard({
  card,
  onUserClick,
  className,
}: LeaderboardCardProps) {
  return (
    <Card className={cn("mb-4", className)}>
      <CardHeader>
        <CardTitle className="text-lg font-gilroy font-semibold">
          {card.title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {card.users.length === 0 ? (
          <p className="text-sm text-muted-foreground">Geen gebruikers in deze categorie.</p>
        ) : (
          <div className="space-y-3">
            {card.users
              .filter((user) => user.name) // Only show users with a valid name
              .map((user, index) => {
              const roleImage = getRoleImage(user.primary_role);
              const handleUserClick = () => onUserClick?.(user.user_id);
              
              return (
                <div
                  key={user.user_id}
                  className={cn(
                    "flex items-center gap-3 py-2 px-3 rounded-lg",
                    "hover:bg-muted/50 transition-colors",
                    onUserClick && "cursor-pointer"
                  )}
                  onClick={handleUserClick}
                >
                  {/* Avatar */}
                  <div className="flex-shrink-0">
                    {user.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.name || "User"}
                        className="w-10 h-10 rounded-full object-cover"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUserClick();
                        }}
                      />
                    ) : (
                      <div
                        className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-sm cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUserClick();
                        }}
                      >
                        {getInitials(user.name)}
                      </div>
                    )}
                  </div>

                  {/* Name + Role Image + Context */}
                  <div className="flex-1 min-w-0 flex items-center gap-2">
                    {user.name && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUserClick();
                        }}
                        className="text-sm font-gilroy font-medium text-foreground hover:text-primary hover:underline transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 rounded truncate"
                      >
                        {user.name}
                      </button>
                    )}
                    {roleImage && (
                      <img
                        src={roleImage}
                        alt={roleDisplayName(user.primary_role) || ""}
                        className="w-10 h-10 flex-shrink-0 object-contain"
                        aria-hidden="true"
                      />
                    )}
                  </div>

                  {/* Context (if available) - shown on the right */}
                  {user.context && (
                    <div className="flex-shrink-0 text-xs text-muted-foreground truncate max-w-[120px]">
                      {user.context}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


// Frontend/src/components/onecikanlar/LeaderboardCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { roleDisplayName } from "@/lib/roleDisplay";
import type { LeaderboardCard as LeaderboardCardType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

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
            {card.users.map((user, index) => (
              <div
                key={user.user_id}
                className={cn(
                  "flex items-center justify-between py-2 px-3 rounded-lg",
                  "hover:bg-muted/50 transition-colors",
                  onUserClick && "cursor-pointer"
                )}
                onClick={() => onUserClick?.(user.user_id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground truncate">
                      {user.name || "Anonieme gebruiker"}
                    </span>
                    {user.role && (
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        · {user.role.includes(" · ") 
                          ? user.role.split(" · ").map(r => roleDisplayName(r.trim())).filter(r => r).join(" · ")
                          : roleDisplayName(user.role)}
                      </span>
                    )}
                  </div>
                  {user.context && (
                    <p className="text-xs text-muted-foreground mt-1 truncate">
                      {user.context}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


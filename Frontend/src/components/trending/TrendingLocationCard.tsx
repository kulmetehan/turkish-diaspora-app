// Frontend/src/components/trending/TrendingLocationCard.tsx
import { useNavigate } from "react-router-dom";
import { TrendingUp, MapPin } from "lucide-react";
import { cn } from "@/lib/ui/cn";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import type { TrendingLocation } from "@/lib/api";

interface TrendingLocationCardProps {
  location: TrendingLocation;
  className?: string;
}

export function TrendingLocationCard({ location, className }: TrendingLocationCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/#/locations/${location.location_id}`);
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={`Trending location: ${location.name}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "cursor-pointer transition-all hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
        className
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <h3 className="font-semibold text-foreground truncate">{location.name}</h3>
                {location.has_verified_badge && <VerifiedBadge size="sm" />}
                {location.is_promoted && (
                  <Badge variant="default" className="bg-yellow-500 text-yellow-900 dark:bg-yellow-600 dark:text-yellow-100">
                    Promoted
                  </Badge>
                )}
              </div>
              <Badge variant="outline" className="flex-shrink-0">
                <TrendingUp className="w-3 h-3 mr-1" />
                #{location.rank}
              </Badge>
            </div>
            
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
              <MapPin className="w-3 h-3" />
              <span className="capitalize">{location.city_key}</span>
              {location.category_key && (
                <>
                  <span>•</span>
                  <span className="capitalize">{location.category_key.replace(/_/g, " ")}</span>
                </>
              )}
            </div>
            
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>{location.check_ins_count} check-ins</span>
              {location.reactions_count > 0 && <span>{location.reactions_count} reacties</span>}
              {location.notes_count > 0 && <span>{location.notes_count} notities</span>}
            </div>
          </div>
          
          <div className="flex-shrink-0 text-right">
            <div className="text-lg font-bold text-primary">
              {location.score.toFixed(1)}
            </div>
            <div className="text-xs text-muted-foreground">score</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


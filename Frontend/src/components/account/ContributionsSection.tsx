import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMyContributions, type ContributionsResponse } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { Icon } from "@/components/Icon";
import { formatDistanceToNow } from "date-fns";
import { nl } from "date-fns/locale";
import { writeViewMode, writeFocusId } from "@/lib/routing/viewMode";

interface ContributionsSectionProps {
  className?: string;
}

export function ContributionsSection({ className }: ContributionsSectionProps) {
  const [contributions, setContributions] = useState<ContributionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLocationClick = (locationId: number) => {
    // Navigate to map with focus
    navigate("/map");
    // Use routing utilities to set focus
    writeViewMode("map");
    writeFocusId(String(locationId));
  };

  useEffect(() => {
    async function fetchContributions() {
      try {
        setLoading(true);
        setError(null);
        const data = await getMyContributions();
        setContributions(data);
      } catch (err) {
        console.error("Failed to fetch contributions:", err);
        setError("Failed to load contributions");
      } finally {
        setLoading(false);
      }
    }

    fetchContributions();
  }, []);

  if (loading) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Bijdragen
          </h2>
          <p className="text-sm text-muted-foreground">Laden...</p>
        </div>
      </div>
    );
  }

  if (error || !contributions) {
    return null; // Don't show section if there's an error
  }

  const hasAnyContributions =
    contributions.last_notes.length > 0 ||
    contributions.last_check_ins.length > 0 ||
    contributions.poll_response_count > 0;

  if (!hasAnyContributions) {
    return null; // Don't show section if no contributions
  }

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-6", className)}>
      <div className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">
            Bijdragen
          </h2>
          <p className="text-sm text-muted-foreground">
            Je laatste bijdragen aan de community
          </p>
        </div>

        {/* Last Notes (Söz) */}
        {contributions.last_notes.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-foreground">Laatste Söz</h3>
            <div className="space-y-2">
              {contributions.last_notes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => handleLocationClick(note.location_id)}
                  className="w-full flex items-start gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors text-left"
                >
                  <Icon name="MessageCircle" className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {note.location_name}
                    </p>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {note.content_preview}
                      {note.content_preview.length >= 50 ? "..." : ""}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(note.created_at), {
                        addSuffix: true,
                        locale: nl,
                      })}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Last Check-ins */}
        {contributions.last_check_ins.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-foreground">Laatste Check-ins</h3>
            <div className="space-y-2">
              {contributions.last_check_ins.map((checkIn) => (
                <button
                  key={checkIn.id}
                  type="button"
                  onClick={() => handleLocationClick(checkIn.location_id)}
                  className="w-full flex items-start gap-2 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors text-left"
                >
                  <Icon name="MapPin" className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {checkIn.location_name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(checkIn.created_at), {
                        addSuffix: true,
                        locale: nl,
                      })}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Poll Responses */}
        {contributions.poll_response_count > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-foreground">Poll-bijdragen</h3>
            <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
                  <Icon name="BarChart3" className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <p className="text-sm text-foreground">
                {contributions.poll_response_count} poll-bijdragen
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// Frontend/src/components/feed/ActivityCard.tsx
import { ReportButton } from "@/components/report/ReportButton";
import type { ActivityItem } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ActivityTypeIcon } from "./ActivityTypeIcon";

interface ActivityCardProps {
  item: ActivityItem;
  className?: string;
}

function formatActivityTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "zojuist";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} min geleden`;
  } else if (diffHours < 24) {
    return `${diffHours} u geleden`;
  } else if (diffDays < 7) {
    return `${diffDays} dag${diffDays > 1 ? "en" : ""} geleden`;
  } else {
    try {
      return new Intl.DateTimeFormat("nl-NL", {
        day: "2-digit",
        month: "short",
        year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
      }).format(date);
    } catch {
      return date.toLocaleDateString("nl-NL");
    }
  }
}

function getActivityMessage(item: ActivityItem): string {
  const locationName = item.location_name || "een locatie";

  switch (item.activity_type) {
    case "check_in":
      return `heeft ingecheckt bij ${locationName}`;
    case "reaction":
      const reactionType = (item.payload?.reaction_type as string) || "🔥";
      const reactionEmoji: Record<string, string> = {
        fire: "🔥",
        heart: "❤️",
        thumbs_up: "👍",
        smile: "😊",
        star: "⭐",
        flag: "🚩",
      };
      const emoji = reactionEmoji[reactionType] || reactionType;
      return `reageerde met ${emoji} op ${locationName}`;
    case "note":
      const notePreview = (item.payload?.content as string)?.substring(0, 100) || "";
      return `schreef een notitie over ${locationName}: "${notePreview}${notePreview.length >= 100 ? "..." : ""}"`;
    case "poll_response":
      return `heeft gestemd op een poll`;
    case "favorite":
      return `heeft ${locationName} toegevoegd aan favorieten`;
    case "bulletin_post":
      const title = (item.payload?.title as string) || "";
      return `heeft een advertentie geplaatst: "${title}"`;
    default:
      return `heeft activiteit op ${locationName}`;
  }
}

export function ActivityCard({ item, className }: ActivityCardProps) {
  const navigate = useNavigate();
  const timeLabel = useMemo(() => formatActivityTime(item.created_at), [item.created_at]);
  const activityMessage = useMemo(() => getActivityMessage(item), [item]);

  const handleClick = () => {
    if (item.activity_type === "bulletin_post") {
      navigate(`/#/feed?tab=bulletin&post=${item.payload?.bulletin_post_id || ''}`);
    } else if (item.location_id) {
      navigate(`/#/locations/${item.location_id}`);
    }
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if ((event.key === "Enter" || event.key === " ") && (item.location_id || item.activity_type === "bulletin_post")) {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role={item.location_id || item.activity_type === "bulletin_post" ? "button" : undefined}
      tabIndex={item.location_id || item.activity_type === "bulletin_post" ? 0 : undefined}
      aria-label={item.activity_type === "bulletin_post"
        ? `Ga naar advertentie: ${item.payload?.title || ''}`
        : (item.location_id ? `Ga naar locatie: ${item.location_name}` : undefined)}
      onClick={item.location_id || item.activity_type === "bulletin_post" ? handleClick : undefined}
      onKeyDown={item.location_id || item.activity_type === "bulletin_post" ? handleKeyDown : undefined}
      className={cn(
        "flex items-start gap-3 rounded-xl border border-border/80 bg-card p-4 shadow-soft transition-all",
        item.location_id
          ? "cursor-pointer hover:border-border hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
          : "",
        className,
      )}
    >
      <div className="flex-shrink-0">
        <ActivityTypeIcon activityType={item.activity_type} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm font-gilroy font-normal text-foreground">
                <span className="font-gilroy font-medium">Iemand</span> {activityMessage}
              </p>
              {item.is_promoted && (
                <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-gilroy font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                  Promoted
                </span>
              )}
            </div>
            {item.location_name && (
              <p className="mt-1 text-xs font-gilroy font-normal text-muted-foreground">{item.location_name}</p>
            )}
            <p className="mt-1 text-xs font-gilroy font-normal text-muted-foreground">{timeLabel}</p>
          </div>
          {/* Report button for notes and reactions */}
          {(item.activity_type === "note" || item.activity_type === "reaction") && (
            <ReportButton
              reportType={item.activity_type}
              targetId={item.id} // Using activity_stream.id for now
              targetName={item.location_name || undefined}
              variant="ghost"
              size="icon"
              className="flex-shrink-0"
            />
          )}
        </div>
      </div>
    </div>
  );
}


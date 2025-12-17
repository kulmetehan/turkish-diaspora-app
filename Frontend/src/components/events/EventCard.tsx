import type { EventItem } from "@/api/events";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/ui/cn";

import {
  eventHasCoordinates,
  formatCityLabel,
  formatEventDateRange
} from "./eventFormatters";

type EventCardProps = {
  event: EventItem;
  selected?: boolean;
  onSelect?: (event: EventItem) => void;
  onOpenDetail?: (event: EventItem) => void;
  onShowOnMap?: (event: EventItem) => void;
};

export function EventCard({
  event,
  selected = false,
  onSelect,
  onOpenDetail,
  onShowOnMap,
}: EventCardProps) {
  const showMapButton = Boolean(onShowOnMap && eventHasCoordinates(event));

  return (
    <div
      role="button"
      tabIndex={0}
      data-selected={selected ? "true" : "false"}
      className={cn(
        "rounded-2xl border border-border/80 bg-card px-5 py-4 text-foreground shadow-soft transition-all duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "hover:border-border hover:shadow-card",
        selected && "border-primary shadow-card",
      )}
      onClick={() => onSelect?.(event)}
      onKeyDown={(eventKeyboard) => {
        if (eventKeyboard.key === "Enter" || eventKeyboard.key === " ") {
          eventKeyboard.preventDefault();
          onSelect?.(event);
        }
      }}
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div className="space-y-1">
            <p className="text-base font-gilroy font-semibold text-foreground line-clamp-2">{event.title}</p>
            <p className="text-sm font-gilroy font-normal text-muted-foreground">{formatEventDateRange(event.start_time_utc, event.end_time_utc)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {event.city_key ? (
              <Badge variant="secondary" className="capitalize">
                <Icon name="MapPin" className="mr-1 h-3.5 w-3.5" aria-hidden />
                {formatCityLabel(event.city_key)}
              </Badge>
            ) : null}
          </div>
        </div>
        {event.location_text ? (
          <p className="text-sm font-gilroy font-normal text-muted-foreground line-clamp-1">{event.location_text}</p>
        ) : null}
        {event.description ? (
          <p className="text-sm font-gilroy font-normal text-muted-foreground line-clamp-3">{event.description}</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
        {showMapButton ? (
          <button
            type="button"
            className="text-xs font-gilroy font-medium text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            onClick={(e) => {
              e.stopPropagation();
              onShowOnMap?.(event);
            }}
          >
            Toon op kaart
          </button>
        ) : null}
        {event.url ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              window.open(event.url, "_blank", "noopener,noreferrer");
            }}
            className={cn(
              "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
            )}
          >
            Eventpagina
          </button>
        ) : null}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onOpenDetail?.(event);
          }}
          className={cn(
            "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
            "bg-primary/90 text-primary-foreground shadow-soft"
          )}
        >
          Details
        </button>
      </div>
    </div>
  );
}

export default EventCard;



import type { EventItem } from "@/api/events";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

import {
  eventHasCoordinates,
  formatCategoryLabel,
  formatCityLabel,
  formatEventDateRange,
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
        "rounded-xl border bg-card px-4 py-4 transition-all duration-150 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "hover:bg-accent/40 hover:shadow-sm",
        selected && "bg-accent/60 border-l-4 border-brand-red shadow-md",
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
            <p className="text-base font-semibold text-foreground line-clamp-2">{event.title}</p>
            <p className="text-sm text-muted-foreground">{formatEventDateRange(event.start_time_utc, event.end_time_utc)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {event.city_key ? (
              <Badge variant="secondary" className="capitalize">
                <Icon name="MapPin" className="mr-1 h-3.5 w-3.5" aria-hidden />
                {formatCityLabel(event.city_key)}
              </Badge>
            ) : null}
            {event.category_key ? (
              <Badge variant="outline" className="capitalize">
                {formatCategoryLabel(event.category_key)}
              </Badge>
            ) : null}
          </div>
        </div>
        {event.location_text ? (
          <p className="text-sm text-muted-foreground line-clamp-2">{event.location_text}</p>
        ) : null}
        {event.description ? (
          <p className="text-sm text-muted-foreground line-clamp-3">{event.description}</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
        {showMapButton ? (
          <button
            type="button"
            className="text-xs text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            onClick={(e) => {
              e.stopPropagation();
              onShowOnMap?.(event);
            }}
          >
            Toon op kaart
          </button>
        ) : null}
        {event.url ? (
          <Button
            asChild
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <a href={event.url} target="_blank" rel="noopener noreferrer">
              Eventpagina
            </a>
          </Button>
        ) : null}
        <Button
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onOpenDetail?.(event);
          }}
        >
          Details
        </Button>
      </div>
    </div>
  );
}

export default EventCard;



import { useMemo } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import type { EventItem } from "@/api/events";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/ui/cn";

import { formatCategoryLabel, formatCityLabel, formatEventDateRange } from "./eventFormatters";

type EventDetailOverlayProps = {
  event: EventItem | null;
  open: boolean;
  onClose: () => void;
};

const DESCRIPTION_THRESHOLD = 160;

export function EventDetailOverlay({ event, open, onClose }: EventDetailOverlayProps) {
  const dateLabel = useMemo(() => {
    if (!event) return "Datum onbekend";
    return formatEventDateRange(event.start_time_utc, event.end_time_utc);
  }, [event]);

  const description = event?.description?.trim() ?? "";
  const summary = event?.summary_ai?.trim() ?? "";
  const hasDescription = description.length > 0;
  const shouldShowSummary = summary.length > 0 && description.length < DESCRIPTION_THRESHOLD;

  return (
    <DialogPrimitive.Root
      open={Boolean(event) && open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-[55] bg-black/20 backdrop-blur-sm data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        {event ? (
        <DialogPrimitive.Content
          className={cn(
            "fixed inset-x-0 bottom-0 top-auto z-[60] mx-auto w-full max-w-screen-sm",
            "flex max-h-[min(80vh,620px)] flex-col rounded-t-3xl border border-border/80 bg-background text-foreground shadow-2xl",
            "px-5 pt-6 pb-[calc(env(safe-area-inset-bottom)+20px)]",
            "focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-bottom",
            "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:max-h-[85vh] lg:w-[min(90vw,840px)] lg:-translate-x-1/2 lg:-translate-y-1/2",
            "lg:rounded-2xl lg:px-6 lg:pb-6 lg:shadow-2xl",
            "lg:data-[state=open]:zoom-in-95 lg:data-[state=closed]:zoom-out-95",
          )}
          aria-labelledby="event-detail-title"
          aria-describedby="event-detail-description"
        >
          <header className="flex flex-col gap-4 border-b pb-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 flex-1 space-y-3">
              <div>
                <DialogPrimitive.Title
                  id="event-detail-title"
                  className="truncate text-2xl font-semibold tracking-tight"
                >
                  {event.title}
                </DialogPrimitive.Title>
                <p className="mt-1 text-sm text-muted-foreground">{dateLabel}</p>
                <div className="mt-2 h-[3px] w-12 rounded-full bg-brand-redSoft" />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {event.city_key && (
                  <Badge variant="secondary" className="capitalize">
                    <Icon name="MapPin" className="mr-1 h-3.5 w-3.5" aria-hidden />
                    Regio: {formatCityLabel(event.city_key)}
                  </Badge>
                )}
                {event.category_key && (
                  <Badge variant="outline" className="capitalize">
                    {formatCategoryLabel(event.category_key)}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                  Bron: {event.source_key}
                </Badge>
              </div>
            </div>
            <DialogPrimitive.Close
              className="self-end rounded-full border border-transparent p-2 text-muted-foreground transition hover:border-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Sluit details"
            >
              <Icon name="X" className="h-4 w-4" />
            </DialogPrimitive.Close>
          </header>

          <div id="event-detail-description" className="mt-4 flex-1 overflow-y-auto space-y-4">
            {event.location_text ? (
              <Card className="p-4">
                <div className="flex items-start gap-3">
                  <Icon name="MapPin" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Locatie</p>
                    <p className="mt-1 text-sm leading-snug">{event.location_text}</p>
                  </div>
                </div>
              </Card>
            ) : null}

            {hasDescription ? (
              <Card className="p-4">
                <div className="flex items-start gap-3">
                  <Icon name="AlignLeft" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Beschrijving</p>
                    <p className="mt-1 whitespace-pre-line text-sm leading-snug">{description}</p>
                  </div>
                </div>
              </Card>
            ) : null}

            {shouldShowSummary ? (
              <Card className="p-4">
                <div className="flex items-start gap-3">
                  <Icon name="Sparkles" className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">AI-samenvatting</p>
                    <p className="mt-1 whitespace-pre-line text-sm leading-snug">{summary}</p>
                  </div>
                </div>
              </Card>
            ) : null}
          </div>

          <div className="mt-6 flex flex-col gap-3 border-t pt-4 lg:flex-row lg:justify-between lg:gap-4">
            <p className="text-sm text-muted-foreground">
              Laatst bijgewerkt op{" "}
              {new Intl.DateTimeFormat(undefined, {
                day: "numeric",
                month: "short",
                year: "numeric",
              }).format(new Date(event.updated_at))}
            </p>
            <div className="flex flex-wrap gap-2">
              {event.url && (
                <Button asChild size="sm" variant="default">
                  <a href={event.url} target="_blank" rel="noopener noreferrer">
                    Open eventpagina
                  </a>
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose();
                }}
              >
                Sluiten
              </Button>
            </div>
          </div>
        </DialogPrimitive.Content>
        ) : null}
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export default EventDetailOverlay;



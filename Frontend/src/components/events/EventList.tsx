import { useEffect, useRef } from "react";

import type { EventItem } from "@/api/events";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/ui/cn";

import { EventCard } from "./EventCard";

type EventListProps = {
  events: EventItem[];
  selectedId: number | null;
  onSelect?: (id: number) => void;
  onSelectDetail?: (id: number) => void;
  onShowOnMap?: (event: EventItem) => void;
  isLoading?: boolean;
  isLoadingMore?: boolean;
  error?: string | null;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onRetry?: () => void;
  className?: string;
  scrollTop?: number; // Scroll position to restore
  onScrollPositionChange?: (scrollTop: number) => void; // Callback when scroll position changes
};

function EventListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="rounded-xl border bg-card p-4">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="mt-3 h-4 w-1/2" />
          <Skeleton className="mt-6 h-9 w-full" />
        </div>
      ))}
    </div>
  );
}

export function EventList({
  events,
  selectedId,
  onSelect,
  onSelectDetail,
  onShowOnMap,
  isLoading = false,
  isLoadingMore = false,
  error = null,
  hasMore = false,
  onLoadMore,
  onRetry,
  className,
  scrollTop = 0,
  onScrollPositionChange,
}: EventListProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const scrollRestoredRef = useRef(false);
  const scrollThrottleRef = useRef<number | null>(null);

  // Restore scroll position on mount
  useEffect(() => {
    if (scrollRestoredRef.current || !scrollContainerRef.current || isLoading || events.length === 0) return;

    if (scrollTop > 0) {
      // Use requestAnimationFrame to ensure content is rendered
      requestAnimationFrame(() => {
        if (scrollContainerRef.current && !scrollRestoredRef.current) {
          scrollContainerRef.current.scrollTo({ top: scrollTop, behavior: "auto" });
          scrollRestoredRef.current = true;
        }
      });
    } else {
      scrollRestoredRef.current = true;
    }
  }, [scrollTop, isLoading, events.length]);

  // Handle scroll position changes (throttled)
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !onScrollPositionChange) return;

    const handleScroll = () => {
      if (scrollThrottleRef.current !== null) {
        window.cancelAnimationFrame(scrollThrottleRef.current);
      }

      scrollThrottleRef.current = window.requestAnimationFrame(() => {
        if (container) {
          onScrollPositionChange(container.scrollTop);
        }
      });
    };

    container.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      container.removeEventListener("scroll", handleScroll);
      if (scrollThrottleRef.current !== null) {
        window.cancelAnimationFrame(scrollThrottleRef.current);
        scrollThrottleRef.current = null;
      }
    };
  }, [onScrollPositionChange]);
  if (isLoading && !events.length) {
    return <EventListSkeleton />;
  }

  if (error && !events.length) {
    return (
      <div className="rounded-2xl border border-border/80 bg-card p-6 text-center text-muted-foreground">
        <p>{error}</p>
        {onRetry ? (
          <Button className="mt-4" variant="outline" size="sm" onClick={onRetry}>
            Opnieuw proberen
          </Button>
        ) : null}
      </div>
    );
  }

  if (!isLoading && !events.length) {
    return (
      <div className="rounded-2xl border bg-card p-6 text-center text-muted-foreground">
        Er zijn nog geen events beschikbaar. Kom later terug voor nieuwe activiteiten.
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div
        ref={scrollContainerRef}
        className={cn(
          "rounded-2xl border border-border/80 bg-card divide-y divide-border/80 shadow-soft",
          "overflow-auto",
          "max-h-[calc(100vh-260px)]",
        )}
      >
        {events.map((event) => (
          <div key={event.id} className="p-3">
            <EventCard
              event={event}
              selected={event.id === selectedId}
              onSelect={() => onSelect?.(event.id)}
              onOpenDetail={() => onSelectDetail?.(event.id)}
              onShowOnMap={onShowOnMap ? () => onShowOnMap(event) : undefined}
            />
          </div>
        ))}
      </div>
      {error && events.length ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}
      {(hasMore || isLoadingMore) && onLoadMore ? (
        <div className="flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={onLoadMore}
            disabled={isLoadingMore}
          >
            {isLoadingMore ? "Bezig met laden…" : "Meer events laden"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export default EventList;



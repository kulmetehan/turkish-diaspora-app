import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import type { EventItem } from "@/api/events";
import { EmojiReactions } from "@/components/feed/EmojiReactions";
import { ErrorBoundary } from "@/components/feed/ErrorBoundary";
import { Icon } from "@/components/Icon";
import { Badge } from "@/components/ui/badge";
import { getEventReactions, toggleEventReaction } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

// Module-level cache to persist across component remounts
// Use Map to track both "fetched" and "in-flight" states
const eventReactionsFetchCache = new Map<number, 'fetching' | 'fetched'>();

import {
  eventHasCoordinates,
  formatCityLabel,
  formatEventDateRange
} from "./eventFormatters";
import { type EventCategoryKey } from "@/lib/routing/eventCategories";
import { useTranslation } from "@/hooks/useTranslation";

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
  const { t } = useTranslation();
  const showMapButton = Boolean(onShowOnMap && eventHasCoordinates(event));

  // Reactions state - only for local optimistic updates
  // Use props directly, state only for local changes before API confirms
  const [localReactions, setLocalReactions] = useState<Record<string, number> | null>(null);
  const [localUserReaction, setLocalUserReaction] = useState<string | null | undefined>(undefined);
  const [isLoadingReactions, setIsLoadingReactions] = useState(false);
  
  // Track current event ID to reset local state when event changes
  const currentEventIdRef = useRef<number>(event.id);
  
  // Reset local state when event ID changes
  useEffect(() => {
    if (currentEventIdRef.current !== event.id) {
      currentEventIdRef.current = event.id;
      setLocalReactions(null);
      setLocalUserReaction(undefined);
    }
  }, [event.id]);

  // Use local state if available (optimistic update), otherwise use props
  const reactions = localReactions !== null ? localReactions : (event.reactions as Record<string, number> || {});
  const userReaction = localUserReaction !== undefined ? localUserReaction : (event.user_reaction || null);

  // Fetch reactions on mount if not provided
  // Use module-level cache to persist across component remounts
  useEffect(() => {
    // Only fetch if:
    // 1. Reactions are not provided in props
    // 2. We haven't fetched yet for this event (checked in module-level cache)
    // 3. We're not currently loading
    // Don't check reactions state here - it may be stale. Only check props.
    const hasReactionsFromProps = !!event.reactions;
    const cacheState = eventReactionsFetchCache.get(event.id);
    const hasFetched = cacheState === 'fetched' || cacheState === 'fetching';
    const shouldFetch = !hasReactionsFromProps && !isLoadingReactions && !hasFetched;

    if (shouldFetch) {
      // Set cache to 'fetching' IMMEDIATELY to prevent race conditions with other mounting components
      eventReactionsFetchCache.set(event.id, 'fetching');
      setIsLoadingReactions(true);
      getEventReactions(event.id)
        .then((data) => {
          // Mark as fetched in cache
          eventReactionsFetchCache.set(event.id, 'fetched');
          // Update local state with fetched data
          setLocalReactions(data.reactions || {});
          setLocalUserReaction(data.user_reaction || null);
        })
        .catch((error) => {
          console.error("Failed to fetch event reactions:", error);
          eventReactionsFetchCache.delete(event.id); // Allow retry on error
        })
        .finally(() => {
          setIsLoadingReactions(false);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.id]);

  const handleReactionToggle = async (reactionType: string) => {
    const previousReactions = reactions;
    const previousUserReaction = userReaction;

    // Optimistic update - use local state
    if (userReaction === reactionType) {
      // Remove reaction
      const newReactions = { ...reactions };
      const currentCount = newReactions[reactionType] || 0;
      if (currentCount <= 1) {
        delete newReactions[reactionType];
      } else {
        newReactions[reactionType] = currentCount - 1;
      }
      setLocalReactions(newReactions);
      setLocalUserReaction(null);
    } else {
      // Add or change reaction
      const newReactions = { ...reactions };
      if (userReaction) {
        // Remove old reaction count
        const oldCount = newReactions[userReaction] || 0;
        if (oldCount <= 1) {
          delete newReactions[userReaction];
        } else {
          newReactions[userReaction] = oldCount - 1;
        }
      }
      newReactions[reactionType] = (newReactions[reactionType] || 0) + 1;
      setLocalReactions(newReactions);
      setLocalUserReaction(reactionType);
    }

    try {
      const result = await toggleEventReaction(event.id, reactionType);
      // Refresh from server to get accurate state
      const updatedData = await getEventReactions(event.id);
      setLocalReactions(updatedData.reactions || {});
      setLocalUserReaction(updatedData.user_reaction || null);
    } catch (error) {
      // Rollback on error - clear local state to use props again
      setLocalReactions(null);
      setLocalUserReaction(undefined);
      toast.error(t("events.card.reactionUpdateError"));
      console.error("Failed to toggle event reaction:", error);
    }
  };

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
            <p className="text-sm font-gilroy font-normal text-muted-foreground">{formatEventDateRange(event.start_time_utc, event.end_time_utc, t)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {event.category_key ? (
              <Badge variant="secondary" className="capitalize">
                <Icon name="Tags" className="mr-1 h-3.5 w-3.5" aria-hidden />
                {t(`events.categories.${event.category_key as EventCategoryKey}`) || event.category_key}
              </Badge>
            ) : null}
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

      {/* Emoji Reactions */}
      <div className="mt-4" onClick={(e) => e.stopPropagation()}>
        <ErrorBoundary>
          <EmojiReactions
            activityId={event.id}
            reactions={reactions}
            userReaction={userReaction}
            onReactionToggle={handleReactionToggle}
          />
        </ErrorBoundary>
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
            {t("map.showOnMap")}
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



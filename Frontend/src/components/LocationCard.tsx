// Frontend/src/components/LocationCard.tsx

import { useEffect, useState } from "react";
import { toast } from "sonner";

import type { LocationMarker } from "@/api/fetchLocations";
import { EmojiReactions } from "@/components/feed/EmojiReactions";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { useTranslation } from "@/hooks/useTranslation";
import type { ReactionType } from "@/lib/api";
import { getLocationReactions, toggleLocationReaction } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

// Module-level cache to persist across component remounts
// Use Map to track both "fetched" and "in-flight" states
const locationReactionsFetchCache = new Map<number, 'fetching' | 'fetched'>();

type Props = {
  location: LocationMarker;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
};

function getStatusBadge(loc: LocationMarker, t: (key: string) => string): { text: string; className: string } {
  const s = (loc.state ?? "").toUpperCase();
  if (s.includes("VERIFIED")) {
    return {
      text: t("common.status.verified"),
      className:
        "inline-flex items-center rounded-full border border-emerald-400/50 bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-emerald-100",
    };
  }
  if (s.includes("CANDIDATE")) {
    return {
      text: t("common.status.candidate"),
      className:
        "inline-flex items-center rounded-full border border-amber-400/50 bg-amber-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-amber-50",
    };
  }
  if (s.includes("REJECT")) {
    return {
      text: t("common.status.rejected"),
      className:
        "inline-flex items-center rounded-full border border-rose-500/50 bg-rose-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-rose-100",
    };
  }

  return {
    text: t("common.status.unknown"),
    className:
      "inline-flex items-center rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-brand-white/70",
  };
}

const LocationCard: React.FC<Props> = ({ location, isSelected = false, onSelect }) => {
  const { t } = useTranslation();
  const { text: statusText, className: badgeClass } = getStatusBadge(location, t);

  // Reactions state
  const [reactions, setReactions] = useState<Record<string, number>>({});
  const [userReaction, setUserReaction] = useState<ReactionType | null>(null);
  const [isLoadingReactions, setIsLoadingReactions] = useState(false);

  // Fetch reactions on mount if not provided
  // Use module-level cache to persist across component remounts
  useEffect(() => {
    if (!location.id) return;

    const currentLocationId = Number(location.id);
    const cacheState = locationReactionsFetchCache.get(currentLocationId);
    const hasFetched = cacheState === 'fetched' || cacheState === 'fetching';
    const shouldFetch = !isLoadingReactions && !hasFetched;

    if (shouldFetch) {
      // Set cache to 'fetching' IMMEDIATELY to prevent race conditions with other mounting components
      locationReactionsFetchCache.set(currentLocationId, 'fetching');
      setIsLoadingReactions(true);
      getLocationReactions(currentLocationId)
        .then((data) => {
          // Mark as fetched in cache
          locationReactionsFetchCache.set(currentLocationId, 'fetched');
          setReactions(data.reactions || {});
          setUserReaction(data.user_reaction);
        })
        .catch((error) => {
          console.error("Failed to fetch location reactions:", error);
          locationReactionsFetchCache.delete(currentLocationId); // Allow retry on error
        })
        .finally(() => {
          setIsLoadingReactions(false);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.id]);

  const handleReactionToggle = async (reactionType: ReactionType) => {
    if (!location.id) return;

    const previousReactions = { ...reactions };
    const previousUserReaction = userReaction;

    // Optimistic update
    if (userReaction === reactionType) {
      // Remove reaction
      setUserReaction(null);
      setReactions((prev) => {
        const newReactions = { ...prev };
        const currentCount = newReactions[reactionType] || 0;
        if (currentCount <= 1) {
          delete newReactions[reactionType];
        } else {
          newReactions[reactionType] = currentCount - 1;
        }
        return newReactions;
      });
    } else {
      // Add or change reaction
      if (userReaction) {
        // Remove old reaction count
        setReactions((prev) => {
          const newReactions = { ...prev };
          const oldCount = newReactions[userReaction] || 0;
          if (oldCount <= 1) {
            delete newReactions[userReaction];
          } else {
            newReactions[userReaction] = oldCount - 1;
          }
          return newReactions;
        });
      }
      setUserReaction(reactionType);
      setReactions((prev) => ({
        ...prev,
        [reactionType]: (prev[reactionType] || 0) + 1,
      }));
    }

    try {
      const result = await toggleLocationReaction(Number(location.id), reactionType);
      // Refresh from server to get accurate state
      const updatedData = await getLocationReactions(Number(location.id));
      setReactions(updatedData.reactions || {});
      setUserReaction(updatedData.user_reaction);
    } catch (error) {
      // Rollback on error
      setReactions(previousReactions);
      setUserReaction(previousUserReaction);
      toast.error("Kon reactie niet bijwerken. Probeer het opnieuw.");
      console.error("Failed to toggle location reaction:", error);
    }
  };

  const handleClick = () => {
    if (onSelect && location.id) onSelect(location.id);
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-selected={isSelected}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "my-2 cursor-pointer rounded-3xl border border-border bg-card p-4 text-foreground shadow-soft transition-all duration-200",
        "hover:border-brand-accent hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        isSelected &&
        "border-transparent bg-[hsl(var(--brand-red-strong))] text-brand-white shadow-[0_30px_45px_rgba(0,0,0,0.55)]",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <h3 className="text-base leading-tight m-0 font-semibold truncate">{location.name}</h3>
          {location.has_verified_badge && <VerifiedBadge size="sm" />}
        </div>
        <span className={badgeClass}>{statusText}</span>
      </div>

      <div className="mt-2 grid gap-1">
        <div className="grid grid-cols-[110px_1fr] gap-2">
          <span className="text-xs text-muted-foreground">{t("location.category")}</span>
          <span className="text-sm">{location.category_label ?? location.category ?? "—"}</span>
        </div>
      </div>

      {/* Emoji Reactions */}
      {location.id && (
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <EmojiReactions
            activityId={Number(location.id)}
            reactions={reactions}
            userReaction={userReaction}
            onReactionToggle={handleReactionToggle}
          />
        </div>
      )}
    </div>
  );
};

export default LocationCard;

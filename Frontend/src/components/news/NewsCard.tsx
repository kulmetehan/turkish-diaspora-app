import { useEffect, useMemo, useRef, useState } from "react";

import { Bookmark, BookmarkCheck } from "lucide-react";
import { toast } from "sonner";

import type { NewsItem } from "@/api/news";
import { EmojiReactions } from "@/components/feed/EmojiReactions";
import { getNewsReactions, toggleNewsReaction } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

// Module-level cache to persist across component remounts
// Use Map to track both "fetched" and "in-flight" states
const newsReactionsFetchCache = new Map<number, 'fetching' | 'fetched'>();

type NewsCardProps = {
  item: NewsItem;
  onClick?: () => void;
  className?: string;
  isBookmarked?: boolean;
  onToggleBookmark?: () => void;
};

function formatPublishedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  try {
    return new Intl.DateTimeFormat("nl-NL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(date);
  } catch {
    return date.toLocaleDateString();
  }
}

export function NewsCard({
  item,
  onClick,
  className,
  isBookmarked = false,
  onToggleBookmark,
}: NewsCardProps) {
  const { t } = useTranslation();
  const visibleTags = useMemo(() => item.tags.slice(0, 3), [item.tags]);
  const publishedLabel = useMemo(
    () => formatPublishedDate(item.published_at),
    [item.published_at],
  );

  // Reactions state
  const [reactions, setReactions] = useState<Record<string, number>>({});
  const [userReaction, setUserReaction] = useState<string | null>(null);
  const [isLoadingReactions, setIsLoadingReactions] = useState(false);

  // Initialize reactions from item props if available
  // Use a ref to track the last reactions values to avoid unnecessary updates
  const lastReactionsRef = useRef<string | null>(null);
  const lastUserReactionRef = useRef<string | null>(null);

  useEffect(() => {
    // Only update if reactions actually changed (by value, not reference)
    const reactionsKey = item.reactions ? JSON.stringify(item.reactions) : null;
    if (reactionsKey !== lastReactionsRef.current && item.reactions) {
      lastReactionsRef.current = reactionsKey;
      // Use reactions directly as they come from the API (dynamic emoji keys)
      setReactions(item.reactions as Record<string, number>);
    } else if (!item.reactions) {
      lastReactionsRef.current = null;
      setReactions({});
    }

    if (item.user_reaction !== lastUserReactionRef.current) {
      lastUserReactionRef.current = item.user_reaction || null;
      setUserReaction(item.user_reaction || null);
    }
  }, [item.reactions, item.user_reaction]);

  // Fetch reactions on mount if not provided
  // Use module-level cache to persist across component remounts
  useEffect(() => {
    // Only fetch if:
    // 1. Reactions are not provided in props
    // 2. We haven't fetched yet for this item (checked in module-level cache)
    // 3. We're not currently loading
    // Don't check reactions state here - it may be stale. Only check props.
    const hasReactionsFromProps = !!item.reactions;
    const cacheState = newsReactionsFetchCache.get(item.id);
    const hasFetched = cacheState === 'fetched' || cacheState === 'fetching';
    const shouldFetch = !hasReactionsFromProps && !isLoadingReactions && !hasFetched;

    if (shouldFetch) {
      // Set cache to 'fetching' IMMEDIATELY to prevent race conditions with other mounting components
      newsReactionsFetchCache.set(item.id, 'fetching');
      setIsLoadingReactions(true);
      getNewsReactions(item.id)
        .then((data) => {
          // Mark as fetched in cache
          newsReactionsFetchCache.set(item.id, 'fetched');
          // Use reactions directly as they come from the API (dynamic emoji keys)
          setReactions(data.reactions || {});
          setUserReaction(data.user_reaction || null);
        })
        .catch((error) => {
          console.error("Failed to fetch news reactions:", error);
          newsReactionsFetchCache.delete(item.id); // Allow retry on error
        })
        .finally(() => {
          setIsLoadingReactions(false);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  const handleReactionToggle = async (reactionType: string) => {
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
      const result = await toggleNewsReaction(item.id, reactionType);
      // Refresh from server to get accurate state
      const updatedData = await getNewsReactions(item.id);
      setReactions(updatedData.reactions || {});
      setUserReaction(updatedData.user_reaction || null);
    } catch (error) {
      // Rollback on error
      setReactions(previousReactions);
      setUserReaction(previousUserReaction);
      toast.error("Kon reactie niet bijwerken. Probeer het opnieuw.");
      console.error("Failed to toggle news reaction:", error);
    }
  };

  const handleActivate = () => {
    if (onClick) {
      onClick();
      return;
    }
    window.open(item.url, "_blank", "noopener,noreferrer");
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleActivate();
    }
  };

  const handleBookmarkClick: React.MouseEventHandler<HTMLButtonElement> = (event) => {
    event.stopPropagation();
    event.preventDefault();
    onToggleBookmark?.();
  };

  const bookmarkLabel = isBookmarked
    ? `Verwijder "${item.title}" uit opgeslagen`
    : `Sla "${item.title}" op`;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Open nieuwsartikel: ${item.title}`}
      data-article-id={item.id}
      onClick={handleActivate}
      onKeyDown={handleKeyDown}
      className={cn(
        "relative cursor-pointer rounded-xl border border-border/50 bg-card p-3 text-foreground shadow-soft transition-all duration-200",
        "hover:border-border/30 hover:shadow-[0_2px_6px_rgba(15,23,42,0.02),0_1px_2px_rgba(15,23,42,0.01)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className,
      )}
    >
      {onToggleBookmark ? (
        <button
          type="button"
          aria-label={bookmarkLabel}
          aria-pressed={isBookmarked}
          title={bookmarkLabel}
          onClick={handleBookmarkClick}
          className={cn(
            "absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-card/90 text-muted-foreground",
            "transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
          )}
        >
          {isBookmarked ? (
            <BookmarkCheck className="h-4 w-4" aria-hidden />
          ) : (
            <Bookmark className="h-4 w-4" aria-hidden />
          )}
        </button>
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row sm:gap-3 pr-8">
        {/* Image */}
        {item.image_url ? (
          <div className="flex-shrink-0 overflow-hidden rounded-xl border border-border/70 bg-muted sm:h-20 sm:w-24 w-full h-32">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.image_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          </div>
        ) : null}

        {/* Content */}
        <div className="flex flex-1 flex-col gap-2">
          {/* Title */}
          <div>
            <h3 className="text-sm font-gilroy font-medium leading-tight text-foreground">
              {item.title}
            </h3>
            {item.tags?.includes("promoted") && (
              <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-gilroy font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 mt-1">
                {t("news.promoted")}
              </span>
            )}
          </div>

          {/* Snippet */}
          {item.snippet ? (
            <p className="text-sm font-gilroy font-normal text-foreground/90 leading-relaxed line-clamp-2">
              {item.snippet}
            </p>
          ) : null}

          {/* Meta: Source and Date */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-gilroy font-normal text-muted-foreground">{item.source}</span>
            <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
            <span className="text-xs font-gilroy font-normal text-muted-foreground">{publishedLabel}</span>
          </div>

          {/* Tags */}
          {visibleTags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {visibleTags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full border border-border/70 bg-surface-muted px-2 py-0.5 text-xs font-gilroy font-medium capitalize text-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {/* Emoji Reactions */}
      <div className="mt-3 pt-2 px-3 pb-3" onClick={(e) => e.stopPropagation()}>
        <EmojiReactions
          activityId={item.id}
          reactions={reactions}
          userReaction={userReaction}
          onReactionToggle={handleReactionToggle}
        />
      </div>
    </div>
  );
}

export default NewsCard;


import { useMemo } from "react";

import { Bookmark, BookmarkCheck } from "lucide-react";

import type { NewsItem } from "@/api/news";
import { cn } from "@/lib/ui/cn";

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
  const visibleTags = useMemo(() => item.tags.slice(0, 3), [item.tags]);
  const publishedLabel = useMemo(
    () => formatPublishedDate(item.published_at),
    [item.published_at],
  );

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
                Promoted
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
    </div>
  );
}

export default NewsCard;


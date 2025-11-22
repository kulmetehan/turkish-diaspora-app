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
        "relative border rounded-xl p-3.5 cursor-pointer bg-card text-card-foreground transition-colors",
        "hover:bg-accent/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
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
            "absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-full border",
            "bg-background/80 text-muted-foreground transition-colors hover:text-foreground hover:border-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          )}
        >
          {isBookmarked ? (
            <BookmarkCheck className="h-5 w-5" aria-hidden />
          ) : (
            <Bookmark className="h-5 w-5" aria-hidden />
          )}
        </button>
      ) : null}
      <div className="flex flex-col gap-3 sm:flex-row">
        {item.image_url ? (
          <div className="flex-shrink-0 overflow-hidden rounded-lg border bg-muted/40 sm:w-32 sm:h-24">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.image_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          </div>
        ) : null}

        <div className="flex flex-1 flex-col gap-2">
          <div>
            <h3 className="text-base font-semibold leading-tight text-foreground">
              {item.title}
            </h3>
            {item.snippet ? (
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                {item.snippet}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium">{item.source}</span>
            <span className="h-1 w-1 rounded-full bg-muted-foreground/60" aria-hidden />
            <span>{publishedLabel}</span>
          </div>

          {visibleTags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {visibleTags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full bg-brand-redSoft/20 px-2 py-0.5 text-xs font-medium capitalize text-brand-red"
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


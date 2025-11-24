import { Fragment } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

import type { NewsItem } from "@/api/news";

import { NewsCard } from "./NewsCard";
import { NewsCardSkeleton } from "./NewsCardSkeleton";

export interface NewsListProps {
  items: NewsItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  onReload: () => void;
  onLoadMore: () => void;
  className?: string;
  emptyMessage?: string;
  errorMessage?: string;
  isBookmarked?: (id: number) => boolean;
  toggleBookmark?: (item: NewsItem) => void;
}

const LOADING_SKELETON_COUNT = 4;

export function NewsList({
  items,
  isLoading,
  isLoadingMore,
  error,
  hasMore,
  onReload,
  onLoadMore,
  className,
  emptyMessage,
  errorMessage,
  isBookmarked,
  toggleBookmark,
}: NewsListProps) {
  if (isLoading && items.length === 0) {
    return (
      <div className="rounded-3xl border border-border bg-card p-4 text-foreground shadow-soft">
        {Array.from({ length: LOADING_SKELETON_COUNT }).map((_, index) => (
          <NewsCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    const message = errorMessage ?? error;
    return (
      <div className="rounded-3xl border border-border bg-card p-5 text-center text-foreground shadow-soft">
        <p>{message}</p>
        {errorMessage && error ? (
            <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        ) : null}
        <Button
          size="sm"
            className="mt-4 border-border text-foreground"
          onClick={onReload}
          variant="outline"
        >
          Opnieuw proberen
        </Button>
      </div>
    );
  }

  if (!items.length) {
    const message = emptyMessage ?? "Er is op dit moment nog geen nieuws voor jou.";
    return (
      <div className="rounded-3xl border border-border bg-card p-6 text-center text-muted-foreground shadow-soft">
        {message}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-3xl border border-border bg-card text-foreground shadow-soft",
        "divide-y divide-border overflow-auto max-h-[calc(100vh-260px)]",
        className,
      )}
    >
      {items.map((item) => (
        <Fragment key={item.id}>
          <div className="p-3.5">
            <NewsCard
              item={item}
              isBookmarked={isBookmarked?.(item.id)}
              onToggleBookmark={toggleBookmark ? () => toggleBookmark(item) : undefined}
            />
          </div>
        </Fragment>
      ))}
      {(hasMore || isLoadingMore) && (
        <div className="p-3.5">
          {isLoadingMore ? (
            <p className="text-sm text-muted-foreground">Meer nieuws laden…</p>
          ) : (
            <Button size="sm" variant="outline" onClick={onLoadMore} className="border-border text-foreground hover:bg-muted">
              Meer laden
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default NewsList;


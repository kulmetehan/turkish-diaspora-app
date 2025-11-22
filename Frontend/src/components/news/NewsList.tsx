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
      <div className="rounded-xl border bg-card p-4 space-y-3">
        {Array.from({ length: LOADING_SKELETON_COUNT }).map((_, index) => (
          <NewsCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    const message = errorMessage ?? error;
    return (
      <div className="rounded-xl border bg-card p-5 text-center text-muted-foreground">
        <p>{message}</p>
        {errorMessage && error ? (
          <p className="mt-1 text-xs text-muted-foreground/80">{error}</p>
        ) : null}
        <Button
          size="sm"
          className="mt-4"
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
      <div className="rounded-xl border bg-card p-6 text-center text-muted-foreground">
        {message}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-xl border bg-card divide-y overflow-auto",
        "max-h-[calc(100vh-260px)]",
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
            <Button size="sm" variant="outline" onClick={onLoadMore}>
              Meer laden
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default NewsList;


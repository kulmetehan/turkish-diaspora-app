import { Fragment, useEffect, useRef } from "react";

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
  meta?: {
    unavailable_reason?: string;
  };
  scrollTop?: number; // Scroll position to restore
  onScrollPositionChange?: (scrollTop: number) => void; // Callback when scroll position changes
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
  meta,
  scrollTop = 0,
  onScrollPositionChange,
}: NewsListProps) {
  // All hooks must be called unconditionally at the top, before any early returns
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const scrollRestoredRef = useRef(false);
  const scrollThrottleRef = useRef<number | null>(null);

  // Restore scroll position on mount (only when conditions are met)
  useEffect(() => {
    // Guard: only restore if we have items and aren't loading initial data
    if (scrollRestoredRef.current || !scrollContainerRef.current || isLoading || items.length === 0) {
      return;
    }

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
  }, [scrollTop, isLoading, items.length]);

  // Handle scroll position changes (throttled) - only when we have a scrollable container
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

  // Early returns AFTER all hooks have been called
  if (isLoading && items.length === 0) {
    return (
      <div className="rounded-2xl border border-border/80 bg-card p-4 text-foreground shadow-soft">
        {Array.from({ length: LOADING_SKELETON_COUNT }).map((_, index) => (
          <NewsCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    const message = errorMessage ?? error;
    return (
      <div className="rounded-2xl border border-border/80 bg-card p-5 text-center text-foreground shadow-soft">
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

  // Show unavailable message for trending when meta.unavailable_reason is set
  if (!items.length && meta?.unavailable_reason) {
    const reason = meta.unavailable_reason;
    let title = "Trending tijdelijk niet beschikbaar (X API)";
    let message = "De trending onderwerpen zijn momenteel niet beschikbaar. Probeer het later opnieuw.";

    if (reason === "x_trending_unavailable_not_enrolled") {
      title = "X API Access Level Vereist";
      message = "Het trends endpoint is niet beschikbaar voor gratis X Developer accounts. Je hebt minimaal een Basic tier account nodig (€100/maand) om trending topics op te halen. Upgrade je account in de X Developer Portal of gebruik een alternatieve bron voor trending topics.";
    } else if (reason === "x_trending_unavailable_forbidden") {
      title = "X API Toegang Geweigerd";
      message = "De X API heeft toegang geweigerd. Controleer of je App gekoppeld is aan een Project en of de Bearer Token correct is.";
    } else if (reason === "x_trending_unavailable_unauthorized") {
      title = "X API Authenticatie Mislukt";
      message = "De Bearer Token is ongeldig of verlopen. Genereer een nieuwe token in de X Developer Portal.";
    }

    return (
      <div className="rounded-2xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-soft">
        <p className="text-base font-medium text-foreground">
          {title}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          {message}
        </p>
      </div>
    );
  }

  if (!items.length) {
    const message = emptyMessage ?? "Er is op dit moment nog geen nieuws voor jou.";
    return (
      <div className="rounded-2xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-soft">
        {message}
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      className={cn(
        "rounded-2xl border border-border/80 bg-card text-foreground shadow-soft",
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


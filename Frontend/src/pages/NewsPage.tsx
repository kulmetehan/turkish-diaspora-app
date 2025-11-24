import { useCallback, useEffect, useMemo, useState } from "react";

import type { NewsItem } from "@/api/news";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { NewsFeedTabs } from "@/components/news/NewsFeedTabs";
import { NewsList } from "@/components/news/NewsList";
import { NewsSearchBar } from "@/components/news/NewsSearchBar";
import { NewsThemeFilterBar } from "@/components/news/NewsThemeFilterBar";
import { useNewsBookmarks } from "@/hooks/useNewsBookmarks";
import { NEWS_FEED_STALE_MS, useNewsFeed } from "@/hooks/useNewsFeed";
import { useNewsSearch } from "@/hooks/useNewsSearch";
import {
  readNewsFeedFromHash,
  readNewsSearchQueryFromHash,
  subscribeToNewsFeedHashChange,
  writeNewsFeedToHash,
  writeNewsSearchQueryToHash,
  type NewsFeedKey,
} from "@/lib/routing/newsFeed";
import {
  clearNewsThemesFromHash,
  readNewsThemesFromHash,
  writeNewsThemesToHash,
  type NewsThemeKey,
} from "@/lib/routing/newsThemes";
import { cn } from "@/lib/ui/cn";

const FRESHNESS_WARNING_MS = 5 * 60 * 1000;

function themesAreEqual(a: NewsThemeKey[], b: NewsThemeKey[]) {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

export default function NewsPage() {
  const [feed, setFeed] = useState<NewsFeedKey>(() => readNewsFeedFromHash());
  const [themes, setThemes] = useState<NewsThemeKey[]>(() => readNewsThemesFromHash());
  const [searchQuery, setSearchQuery] = useState<string>(() =>
    readNewsSearchQueryFromHash(),
  );

  const { bookmarks, isBookmarked, toggleBookmark } = useNewsBookmarks();

  useEffect(() => {
    const handleHashChange = () => {
      setFeed((current) => {
        const next = readNewsFeedFromHash();
        return current === next ? current : next;
      });
      setThemes((current) => {
        const next = readNewsThemesFromHash();
        return themesAreEqual(current, next) ? current : next;
      });
      setSearchQuery((current) => {
        const next = readNewsSearchQueryFromHash();
        return current === next ? current : next;
      });
    };
    return subscribeToNewsFeedHashChange(handleHashChange);
  }, []);

  useEffect(() => {
    writeNewsFeedToHash(feed);
  }, [feed]);

  useEffect(() => {
    writeNewsThemesToHash(themes);
  }, [themes]);

  useEffect(() => {
    writeNewsSearchQueryToHash(searchQuery);
  }, [searchQuery]);

  const handleFeedChange = useCallback((next: NewsFeedKey) => {
    setFeed((current) => (current === next ? current : next));
  }, []);

  const handleThemesChange = useCallback((next: NewsThemeKey[]) => {
    setThemes((current) => (themesAreEqual(current, next) ? current : next));
  }, []);

  const handleClearThemes = useCallback(() => {
    clearNewsThemesFromHash();
    setThemes([]);
  }, []);

  return (
    <div className="flex w-full flex-col gap-5 px-4 py-6 text-foreground sm:px-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Nieuws voor jou</h1>
        <p className="text-sm text-muted-foreground">
          Artikelen geselecteerd op relevantie voor de Turkse diaspora.
        </p>
      </header>

      <NewsFeedTabs value={feed} onChange={handleFeedChange} />
      {feed === "bookmarks" ? (
        <BookmarksSection
          bookmarks={bookmarks}
          isBookmarked={isBookmarked}
          toggleBookmark={toggleBookmark}
        />
      ) : (
        <StandardNewsSection
          feed={feed}
          themes={themes}
          onThemesChange={handleThemesChange}
          onClearThemes={handleClearThemes}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSearchClear={() => setSearchQuery("")}
          isBookmarked={isBookmarked}
          toggleBookmark={toggleBookmark}
        />
      )}
    </div>
  );
}

interface StandardNewsSectionProps {
  feed: NewsFeedKey;
  themes: NewsThemeKey[];
  onThemesChange: (themes: NewsThemeKey[]) => void;
  onClearThemes: () => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSearchClear: () => void;
  isBookmarked: (id: number) => boolean;
  toggleBookmark: (item: NewsItem) => void;
}

function StandardNewsSection({
  feed,
  themes,
  onThemesChange,
  onClearThemes,
  searchQuery,
  onSearchQueryChange,
  onSearchClear,
  isBookmarked,
  toggleBookmark,
}: StandardNewsSectionProps) {
  const trimmedSearch = searchQuery.trim();
  const isSearchMode = trimmedSearch.length >= 2;
  const isTrendingFeed = feed === "trending";
  /**
   * Trending ondersteunt geen theme filters; geef undefined door zodat de
   * hook geen onnodige renders krijgt door steeds nieuwe lege arrays.
   */
  const effectiveThemes = isTrendingFeed ? undefined : themes;
  const searchEmptyMessage = "Geen artikelen gevonden voor je zoekopdracht.";
  const searchErrorMessage = "Zoeken mislukt. Probeer het later opnieuw.";

  const {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    reload,
    loadMore,
    isReloading,
    lastUpdatedAt,
  } = useNewsFeed({ feed, pageSize: 20, themes: effectiveThemes });

  const {
    items: searchItems,
    isLoading: searchLoading,
    isLoadingMore: searchLoadingMore,
    error: searchError,
    hasMore: searchHasMore,
    reload: searchReload,
    loadMore: searchLoadMore,
  } = useNewsSearch({ query: searchQuery, pageSize: 20 });

  const displayedItems = isSearchMode ? searchItems : items;
  const displayedLoading = isSearchMode ? searchLoading : isLoading;
  const displayedLoadingMore = isSearchMode ? searchLoadingMore : isLoadingMore;
  const displayedError = isSearchMode ? searchError : error;
  const displayedHasMore = isSearchMode ? searchHasMore : hasMore;
  const displayedReload = isSearchMode ? searchReload : reload;
  const displayedLoadMore = isSearchMode ? searchLoadMore : loadMore;
  const isInitialLoading = isLoading && items.length === 0;
  const refreshDisabled = isInitialLoading || isReloading;

  const maybeAutoRefresh = useCallback(() => {
    if (!lastUpdatedAt) return;
    const age = Date.now() - lastUpdatedAt.getTime();
    if (age >= NEWS_FEED_STALE_MS) {
      void reload();
    }
  }, [lastUpdatedAt, reload]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof document === "undefined") {
      return;
    }

    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        maybeAutoRefresh();
      }
    };

    window.addEventListener("focus", handleVisibility);
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.removeEventListener("focus", handleVisibility);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [maybeAutoRefresh]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof document === "undefined") {
      return;
    }
    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        maybeAutoRefresh();
      }
    }, NEWS_FEED_STALE_MS);
    return () => window.clearInterval(intervalId);
  }, [maybeAutoRefresh]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <NewsSearchBar
          value={searchQuery}
          onChange={onSearchQueryChange}
          onClear={onSearchClear}
          loading={isSearchMode && searchLoading}
          className="flex-1"
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Nieuws verversen"
          className="shrink-0 border-border"
          disabled={refreshDisabled}
          onClick={() => {
            const maybePromise = displayedReload();
            if (maybePromise && typeof (maybePromise as Promise<void>).then === "function") {
              void maybePromise;
            }
          }}
        >
          <Icon
            name={isReloading ? "Loader2" : "RotateCcw"}
            className={cn("h-4 w-4", isReloading && "animate-spin")}
            aria-hidden
          />
        </Button>
      </div>

      {isSearchMode ? (
        <p className="px-1 text-xs text-muted-foreground">
          Zoekresultaten binnen de diaspora-feed. Gebruik de tabs om snel terug te
          schakelen naar een vaste feed.
        </p>
      ) : null}

      {!isTrendingFeed ? (
        <NewsThemeFilterBar
          selected={themes}
          onChange={onThemesChange}
          onClear={onClearThemes}
        />
      ) : null}

      <NewsList
        items={displayedItems}
        isLoading={displayedLoading}
        isLoadingMore={displayedLoadingMore}
        error={displayedError}
        hasMore={displayedHasMore}
        onReload={displayedReload}
        onLoadMore={displayedLoadMore}
        emptyMessage={isSearchMode ? searchEmptyMessage : undefined}
        errorMessage={isSearchMode ? searchErrorMessage : undefined}
        isBookmarked={isBookmarked}
        toggleBookmark={toggleBookmark}
      />
    </div>
  );
}

interface BookmarksSectionProps {
  bookmarks: NewsItem[];
  isBookmarked: (id: number) => boolean;
  toggleBookmark: (item: NewsItem) => void;
}

function BookmarksSection({
  bookmarks,
  isBookmarked,
  toggleBookmark,
}: BookmarksSectionProps) {
  if (!bookmarks.length) {
    return (
      <div className="space-y-4">
        <p className="px-1 text-xs text-muted-foreground">
          Je opgeslagen artikelen worden lokaal op dit apparaat bewaard en worden niet
          gesynchroniseerd met andere apparaten.
        </p>
        <div className="rounded-3xl border border-border bg-surface-raised p-6 text-center text-foreground shadow-soft">
          <p className="text-base font-semibold text-foreground">
            Nog geen opgeslagen artikelen
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Gebruik het bookmark-icoon bij een nieuwsbericht om het hier op te slaan.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="px-1 text-xs text-muted-foreground">
        Je opgeslagen artikelen worden lokaal op dit apparaat bewaard en worden niet
        gesynchroniseerd met andere apparaten.
      </p>
      <NewsList
        items={bookmarks}
        isLoading={false}
        isLoadingMore={false}
        error={null}
        hasMore={false}
        onReload={() => undefined}
        onLoadMore={() => undefined}
        isBookmarked={isBookmarked}
        toggleBookmark={toggleBookmark}
      />
    </div>
  );
}

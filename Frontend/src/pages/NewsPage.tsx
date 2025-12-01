import { useCallback, useEffect, useState } from "react";

import type { NewsItem } from "@/api/news";
import { NewsCategoryFilterBar } from "@/components/news/NewsCategoryFilterBar";
import { NewsCityModal } from "@/components/news/NewsCityModal";
import { NewsFeedTabs } from "@/components/news/NewsFeedTabs";
import { NewsList } from "@/components/news/NewsList";
import { NewsSearchBar } from "@/components/news/NewsSearchBar";
import { Button } from "@/components/ui/button";
import { useNewsBookmarks } from "@/hooks/useNewsBookmarks";
import { useNewsCityPreferences, type CityLabelMap } from "@/hooks/useNewsCityPreferences";
import { NEWS_FEED_STALE_MS, useNewsFeed } from "@/hooks/useNewsFeed";
import { useNewsSearch } from "@/hooks/useNewsSearch";
import {
  clearNewsCategoriesFromHash,
  readNewsCategoriesFromHash,
  writeNewsCategoriesToHash,
  type NewsCategoryKey,
} from "@/lib/routing/newsCategories";
import {
  readNewsFeedFromHash,
  readNewsSearchQueryFromHash,
  subscribeToNewsFeedHashChange,
  writeNewsFeedToHash,
  writeNewsSearchQueryToHash,
  type NewsFeedKey,
} from "@/lib/routing/newsFeed";
import { navigationActions, useNewsNavigation } from "@/state/navigation";

function categoriesAreEqual(a: NewsCategoryKey[], b: NewsCategoryKey[]) {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

export default function NewsPage() {
  // Read navigation state from store
  const newsNavigation = useNewsNavigation();

  // Read hash params (for shareable URLs) - these take priority
  const hashFeed = readNewsFeedFromHash();
  const hashCategories = readNewsCategoriesFromHash();
  const hashSearchQuery = readNewsSearchQueryFromHash();

  // Determine if hash has meaningful values (not just defaults)
  const hasHashFeed = hashFeed !== "nl";
  const hasHashCategories = hashCategories.length > 0;
  const hasHashSearch = hashSearchQuery.trim().length > 0;
  const hasHashParams = hasHashFeed || hasHashCategories || hasHashSearch;

  // Priority: hash params (if present) > store values
  // Initialize state: if hash has values, use them (and sync to store), otherwise use store
  const [feed, setFeed] = useState<NewsFeedKey>(() => {
    if (hasHashParams) {
      // Sync hash values to store
      navigationActions.setNews({
        feed: hashFeed,
        categories: hashCategories,
        searchQuery: hashSearchQuery,
      });
      return hashFeed;
    }
    return newsNavigation.feed;
  });

  const [categories, setCategories] = useState<NewsCategoryKey[]>(() => {
    return hasHashParams ? hashCategories : newsNavigation.categories;
  });

  const [searchQuery, setSearchQuery] = useState<string>(() => {
    return hasHashParams ? hashSearchQuery : newsNavigation.searchQuery;
  });

  const [trendCountry, setTrendCountry] = useState<"nl" | "tr">("nl");

  const { bookmarks, isBookmarked, toggleBookmark } = useNewsBookmarks();
  const {
    options: cityOptions,
    preferences: cityPreferences,
    cityLabels,
    ready: cityReady,
    isModalOpen: isCityModalOpen,
    openModal: openCityModal,
    closeModal: closeCityModal,
    savePreferences: saveCityPreferences,
    rememberCityLabels,
  } = useNewsCityPreferences({ currentFeed: feed });

  useEffect(() => {
    if (!cityReady) return;
    if (
      (feed === "local" && cityPreferences.nl.length === 0) ||
      (feed === "origin" && cityPreferences.tr.length === 0)
    ) {
      openCityModal();
    }
  }, [cityReady, cityPreferences, feed, openCityModal]);

  useEffect(() => {
    const handleHashChange = () => {
      const nextFeed = readNewsFeedFromHash();
      const nextCategories = readNewsCategoriesFromHash();
      const nextSearchQuery = readNewsSearchQueryFromHash();

      setFeed((current) => {
        if (current !== nextFeed) {
          // Sync to store when hash changes
          navigationActions.setNews({ feed: nextFeed });
          return nextFeed;
        }
        return current;
      });
      setCategories((current) => {
        if (!categoriesAreEqual(current, nextCategories)) {
          // Sync to store when hash changes
          navigationActions.setNews({ categories: nextCategories });
          return nextCategories;
        }
        return current;
      });
      setSearchQuery((current) => {
        if (current !== nextSearchQuery) {
          // Sync to store when hash changes
          navigationActions.setNews({ searchQuery: nextSearchQuery });
          return nextSearchQuery;
        }
        return current;
      });
    };
    return subscribeToNewsFeedHashChange(handleHashChange);
  }, []);

  useEffect(() => {
    writeNewsFeedToHash(feed);
    // Also update store
    navigationActions.setNews({ feed });
  }, [feed]);

  useEffect(() => {
    writeNewsCategoriesToHash(categories);
    // Also update store
    navigationActions.setNews({ categories });
  }, [categories]);

  useEffect(() => {
    writeNewsSearchQueryToHash(searchQuery);
    // Also update store
    navigationActions.setNews({ searchQuery });
  }, [searchQuery]);

  const handleFeedChange = useCallback((next: NewsFeedKey) => {
    setFeed((current) => (current === next ? current : next));
  }, []);

  const handleCategoriesChange = useCallback((next: NewsCategoryKey[]) => {
    setCategories((current) => (categoriesAreEqual(current, next) ? current : next));
  }, []);

  const handleClearCategories = useCallback(() => {
    clearNewsCategoriesFromHash();
    setCategories([]);
    navigationActions.setNews({ categories: [] });
  }, []);

  const handleScrollPositionChange = useCallback((scrollTop: number) => {
    navigationActions.setNews({ scrollTop });
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-10 text-foreground">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-foreground">Nieuws voor jou</h1>
        <p className="text-sm text-muted-foreground">
          Artikelen geselecteerd op relevantie voor de Turkse diaspora.
        </p>
      </header>
      <section className="rounded-3xl border border-border bg-surface-raised p-4 shadow-soft">
        <NewsFeedTabs value={feed} onChange={handleFeedChange} />
      </section>
      {feed === "bookmarks" ? (
        <BookmarksSection
          bookmarks={bookmarks}
          isBookmarked={isBookmarked}
          toggleBookmark={toggleBookmark}
        />
      ) : (
        <StandardNewsSection
          feed={feed}
          categories={categories}
          onCategoriesChange={handleCategoriesChange}
          onClearCategories={handleClearCategories}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSearchClear={() => setSearchQuery("")}
          isBookmarked={isBookmarked}
          toggleBookmark={toggleBookmark}
          cityPreferences={cityPreferences}
          cityLabels={cityLabels}
          onEditCities={openCityModal}
          trendCountry={trendCountry}
          onTrendCountryChange={setTrendCountry}
          scrollTop={newsNavigation.scrollTop}
          onScrollPositionChange={handleScrollPositionChange}
        />
      )}
      <NewsCityModal
        isOpen={isCityModalOpen}
        options={cityOptions}
        preferences={cityPreferences}
        cityLabels={cityLabels}
        onRememberCities={rememberCityLabels}
        onSave={saveCityPreferences}
        onClose={closeCityModal}
      />
    </div>
  );
}

interface StandardNewsSectionProps {
  feed: NewsFeedKey;
  categories: NewsCategoryKey[];
  onCategoriesChange: (categories: NewsCategoryKey[]) => void;
  onClearCategories: () => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSearchClear: () => void;
  isBookmarked: (id: number) => boolean;
  toggleBookmark: (item: NewsItem) => void;
  cityPreferences: { nl: string[]; tr: string[] };
  cityLabels: CityLabelMap;
  onEditCities: () => void;
  trendCountry: "nl" | "tr";
  onTrendCountryChange: (country: "nl" | "tr") => void;
  scrollTop: number;
  onScrollPositionChange: (scrollTop: number) => void;
}

function StandardNewsSection({
  feed,
  categories,
  onCategoriesChange,
  onClearCategories,
  searchQuery,
  onSearchQueryChange,
  onSearchClear,
  isBookmarked,
  toggleBookmark,
  cityPreferences,
  cityLabels,
  onEditCities,
  trendCountry,
  onTrendCountryChange,
  scrollTop,
  onScrollPositionChange,
}: StandardNewsSectionProps) {
  const trimmedSearch = searchQuery.trim();
  const isSearchMode = trimmedSearch.length >= 2;
  const isTrendingFeed = feed === "trending";
  /**
   * Trending ondersteunt geen category filters; geef undefined door zodat de
   * hook geen onnodige renders krijgt door steeds nieuwe lege arrays.
   */
  const effectiveCategories = isTrendingFeed ? undefined : categories;
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
    meta,
  } = useNewsFeed({
    feed,
    pageSize: 20,
    categories: effectiveCategories,
    citiesNl: feed === "local" ? cityPreferences.nl : undefined,
    citiesTr: feed === "origin" ? cityPreferences.tr : undefined,
    trendCountry: feed === "trending" ? trendCountry : undefined,
  });

  const lastUpdatedLabel = lastUpdatedAt
    ? new Intl.DateTimeFormat("nl-NL", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(lastUpdatedAt)
    : "n.v.t.";

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
    <div className="flex flex-col gap-5">
      <div className="rounded-3xl border border-border bg-surface-raised p-4 shadow-soft">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <NewsSearchBar
            value={searchQuery}
            onChange={onSearchQueryChange}
            onClear={onSearchClear}
            loading={isSearchMode && searchLoading}
            className="flex-1"
          />
        </div>

        {isSearchMode ? (
          <p className="px-1 pt-2 text-xs text-muted-foreground">
            Zoekresultaten binnen de selectie. Gebruik de tabs om snel terug te schakelen naar een vaste feed.
          </p>
        ) : (
          <p className="px-1 pt-2 text-xs text-muted-foreground">
            Laatst bijgewerkt: {lastUpdatedLabel}
          </p>
        )}
        {isTrendingFeed ? (
          <div className="px-1 pt-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Land</span>
              <div className="flex gap-2">
                {(["nl", "tr"] as const).map((country) => (
                  <Button
                    key={`trend-country-${country}`}
                    type="button"
                    size="sm"
                    variant={trendCountry === country ? "default" : "outline"}
                    onClick={() => {
                      if (trendCountry !== country) {
                        onTrendCountryChange(country);
                      }
                    }}
                  >
                    {country === "nl" ? "Nederland" : "Turkije"}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {!isTrendingFeed ? (
        <NewsCategoryFilterBar
          feed={feed}
          selected={categories}
          onChange={onCategoriesChange}
          onClear={onClearCategories}
        />
      ) : null}

      {(feed === "local" || feed === "origin") ? (
        <div className="flex flex-wrap items-center gap-2 rounded-3xl border border-border bg-surface-raised px-4 py-3 text-xs text-muted-foreground shadow-soft">
          <span>
            Steden:&nbsp;
            {feed === "local"
              ? renderCityList(cityPreferences.nl, cityLabels)
              : renderCityList(cityPreferences.tr, cityLabels)}
          </span>
          <Button type="button" variant="ghost" size="sm" onClick={onEditCities}>
            Wijzig selectie
          </Button>
        </div>
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
        meta={!isSearchMode ? meta : undefined}
        scrollTop={scrollTop}
        onScrollPositionChange={onScrollPositionChange}
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
        <div className="rounded-3xl border border-border bg-card p-6 text-center text-foreground shadow-soft">
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

function renderCityList(cities: string[], cityLabels: CityLabelMap) {
  if (!cities.length) {
    return "geen selectie";
  }
  return cities.map((key) => cityLabels[key]?.name ?? key).join(", ");
}

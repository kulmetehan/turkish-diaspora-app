import { useCallback, useEffect, useRef, useState } from "react";

import type { NewsItem } from "@/api/news";
import { AppHeader } from "@/components/feed/AppHeader";
import { FooterTabs } from "@/components/FooterTabs";
import { AppViewportShell } from "@/components/layout";
import { NewsCategoryFilterBar } from "@/components/news/NewsCategoryFilterBar";
import { NewsCityModal } from "@/components/news/NewsCityModal";
import { NewsCitySelector } from "@/components/news/NewsCitySelector";
import { NewsCountrySelector } from "@/components/news/NewsCountrySelector";
import { NewsFeedTabs } from "@/components/news/NewsFeedTabs";
import { NewsHeaderSearch } from "@/components/news/NewsHeaderSearch";
import { NewsIntroHeading } from "@/components/news/NewsIntroHeading";
import { NewsList } from "@/components/news/NewsList";
import { useNewsBookmarks } from "@/hooks/useNewsBookmarks";
import { useNewsCityPreferences, type CityLabelMap } from "@/hooks/useNewsCityPreferences";
import { NEWS_FEED_STALE_MS, useNewsFeed } from "@/hooks/useNewsFeed";
import { useNewsSearch } from "@/hooks/useNewsSearch";
import { getOnboardingStatus } from "@/lib/api";
import {
  clearNewsCategoriesFromHash,
  readNewsCategoriesFromHash,
  writeNewsCategoriesToHash,
  type NewsCategoryKey,
} from "@/lib/routing/newsCategories";
import {
  clearNewsArticleIdFromHash,
  readNewsArticleIdFromHash,
  readNewsFeedFromHash,
  readNewsSearchQueryFromHash,
  subscribeToNewsFeedHashChange,
  writeNewsFeedToHash,
  writeNewsSearchQueryToHash,
  type NewsFeedKey,
} from "@/lib/routing/newsFeed";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import { navigationActions, useNewsNavigation } from "@/state/navigation";

function categoriesAreEqual(a: NewsCategoryKey[], b: NewsCategoryKey[]) {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

export default function NewsPage() {
  const seo = useSeo();
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
    if (hasHashParams) {
      return hashCategories;
    }
    // Default to "general" for NL/TR feeds if no categories are set
    const storeCategories = newsNavigation.categories;
    const currentFeed = hasHashParams ? hashFeed : newsNavigation.feed;
    if (storeCategories.length === 0 && (currentFeed === "nl" || currentFeed === "tr")) {
      return ["general"];
    }
    return storeCategories;
  });

  const [searchQuery, setSearchQuery] = useState<string>(() => {
    return hasHashParams ? hashSearchQuery : newsNavigation.searchQuery;
  });

  // Read trend_country from hash on mount
  const hashParams = (() => {
    if (typeof window === "undefined") return new URLSearchParams();
    const hash = window.location.hash ?? "";
    const queryIndex = hash.indexOf("?");
    const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
    return new URLSearchParams(query);
  })();
  const hashTrendCountry = hashParams.get("trend_country") as "nl" | "tr" | null;
  const [trendCountry, setTrendCountry] = useState<"nl" | "tr">(() => {
    return (hashTrendCountry === "nl" || hashTrendCountry === "tr") ? hashTrendCountry : "nl";
  });
  const [showSearch, setShowSearch] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const scrollRestoredRef = useRef(false);
  const scrollThrottleRef = useRef<number | null>(null);

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

    // Check onboarding status
    const onboardingStatus = getOnboardingStatus();

    // Only show modal if:
    // 1. Onboarding is NOT completed AND cities are missing for the current feed
    // 2. OR: Onboarding is completed but cities are still missing (edge case - user skipped cities)
    const shouldShowModal =
      (!onboardingStatus.onboarding_completed ||
        (feed === "local" && cityPreferences.nl.length === 0) ||
        (feed === "origin" && cityPreferences.tr.length === 0)) &&
      ((feed === "local" && cityPreferences.nl.length === 0) ||
        (feed === "origin" && cityPreferences.tr.length === 0));

    if (shouldShowModal) {
      openCityModal();
    }
  }, [cityReady, cityPreferences, feed, openCityModal]);

  useEffect(() => {
    const handleHashChange = () => {
      const nextFeed = readNewsFeedFromHash();
      const nextCategories = readNewsCategoriesFromHash();
      const nextSearchQuery = readNewsSearchQueryFromHash();
      // Read trend_country from hash
      const hashParams = (() => {
        if (typeof window === "undefined") return new URLSearchParams();
        const hash = window.location.hash ?? "";
        const queryIndex = hash.indexOf("?");
        const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
        return new URLSearchParams(query);
      })();
      const nextTrendCountry = hashParams.get("trend_country") as "nl" | "tr" | null;

      setFeed((current) => {
        if (current !== nextFeed) {
          return nextFeed;
        }
        return current;
      });
      setCategories((current) => {
        if (!categoriesAreEqual(current, nextCategories)) {
          return nextCategories;
        }
        return current;
      });
      setSearchQuery((current) => {
        if (current !== nextSearchQuery) {
          return nextSearchQuery;
        }
        return current;
      });
      // Update trendCountry when hash changes
      if (nextTrendCountry === "nl" || nextTrendCountry === "tr") {
        setTrendCountry((current) => {
          if (current !== nextTrendCountry) {
            return nextTrendCountry;
          }
          return current;
        });
      }
    };
    return subscribeToNewsFeedHashChange(handleHashChange);
  }, [trendCountry]);

  useEffect(() => {
    writeNewsFeedToHash(feed);
    // Also update store
    navigationActions.setNews({ feed });
  }, [feed]);

  // Auto-select "general" category when switching to "nl" or "tr" feeds
  useEffect(() => {
    if ((feed === "nl" || feed === "tr") && categories.length === 0) {
      const defaultCategories: NewsCategoryKey[] = ["general"];
      setCategories(defaultCategories);
      writeNewsCategoriesToHash(defaultCategories);
      navigationActions.setNews({ categories: defaultCategories });
    }
  }, [feed, categories]);

  // Sync default "general" category to hash and store on mount if needed
  useEffect(() => {
    const initialFeed = hasHashParams ? hashFeed : newsNavigation.feed;
    const initialCategories = hasHashParams ? hashCategories : newsNavigation.categories;
    if (!hasHashParams && (initialFeed === "nl" || initialFeed === "tr") && initialCategories.length === 0) {
      const defaultCategories: NewsCategoryKey[] = ["general"];
      setCategories(defaultCategories);
      writeNewsCategoriesToHash(defaultCategories);
      navigationActions.setNews({ categories: defaultCategories });
    }
  }, []); // Only run on mount

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

  // Restore scroll position on mount
  useEffect(() => {
    if (scrollRestoredRef.current || !scrollContainerRef.current) {
      return;
    }

    const scrollTop = newsNavigation.scrollTop;
    if (scrollTop > 0) {
      requestAnimationFrame(() => {
        if (scrollContainerRef.current && !scrollRestoredRef.current) {
          scrollContainerRef.current.scrollTo({ top: scrollTop, behavior: "auto" });
          scrollRestoredRef.current = true;
        }
      });
    } else {
      scrollRestoredRef.current = true;
    }
  }, [newsNavigation.scrollTop]);

  // Track scroll position changes
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !handleScrollPositionChange) return;

    const handleScroll = () => {
      if (scrollThrottleRef.current !== null) {
        window.cancelAnimationFrame(scrollThrottleRef.current);
      }

      scrollThrottleRef.current = window.requestAnimationFrame(() => {
        if (container) {
          handleScrollPositionChange(container.scrollTop);
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
  }, [handleScrollPositionChange]);

  const handleNotificationClick = useCallback(() => {
    // TODO: Implement notification navigation
    console.log("Notification clicked");
  }, []);

  const handleSearchToggle = useCallback(() => {
    setShowSearch((prev) => !prev);
  }, []);

  const handleSearchClose = useCallback(() => {
    setShowSearch(false);
  }, []);


  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
        <div className="flex flex-col h-full relative">
          {/* Red gradient overlay */}
          <div
            className="absolute inset-x-0 top-0 pointer-events-none z-0"
            style={{
              height: '25%',
              background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
            }}
          />
          <AppHeader
            onNotificationClick={handleNotificationClick}
            showSearch={showSearch}
            onSearchToggle={handleSearchToggle}
          />
          <NewsHeaderSearch
            isOpen={showSearch}
            value={searchQuery}
            onChange={setSearchQuery}
            onClear={() => setSearchQuery("")}
            onClose={handleSearchClose}
            loading={searchQuery.trim().length >= 2}
          />
          <div
            ref={scrollContainerRef}
            className="flex-1 overflow-y-auto px-4 pb-24 relative z-10"
          >
            <NewsIntroHeading />
            {/* City selector for local/origin feeds - positioned under intro, above tabs */}
            {(feed === "local" || feed === "origin") ? (
              <NewsCitySelector
                cities={feed === "local" ? cityPreferences.nl : cityPreferences.tr}
                cityLabels={cityLabels}
                onEdit={openCityModal}
                className="mt-2"
              />
            ) : null}
            {/* Country selector for trending feed - positioned under intro, above tabs */}
            {feed === "trending" ? (
              <NewsCountrySelector
                value={trendCountry}
                onChange={setTrendCountry}
                className="mt-2"
              />
            ) : null}
            <NewsFeedTabs value={feed} onChange={handleFeedChange} className="mt-2" />
            {/* Subtle separator between main tabs and category filters */}
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
                scrollContainerRef={scrollContainerRef}
              />
            )}
          </div>
          <FooterTabs />
        </div>
        <NewsCityModal
          isOpen={isCityModalOpen}
          options={cityOptions}
          preferences={cityPreferences}
          cityLabels={cityLabels}
          onRememberCities={rememberCityLabels}
          onSave={saveCityPreferences}
          onClose={closeCityModal}
        />
      </AppViewportShell>
    </>
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
  scrollContainerRef: React.RefObject<HTMLDivElement>;
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
  scrollContainerRef,
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

  // Scroll to article when article ID is in hash
  const articleIdRef = useRef<number | null>(null);

  // Read article ID from hash on mount and when hash changes
  useEffect(() => {
    const articleId = readNewsArticleIdFromHash();
    if (articleId) {
      articleIdRef.current = articleId;
    }
  }, []);

  // Listen for hash changes
  useEffect(() => {
    const handleHashChange = () => {
      const articleId = readNewsArticleIdFromHash();
      if (articleId) {
        articleIdRef.current = articleId;
      }
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  // Scroll to article when items are loaded
  useEffect(() => {
    const articleId = articleIdRef.current;
    if (!articleId || !scrollContainerRef.current || displayedItems.length === 0) return;

    // Wait for items to load and render
    const scrollToArticle = () => {
      const articleElement = document.querySelector(`[data-article-id="${articleId}"]`);
      if (articleElement && scrollContainerRef.current) {
        const containerRect = scrollContainerRef.current.getBoundingClientRect();
        const elementRect = articleElement.getBoundingClientRect();
        const scrollTop = scrollContainerRef.current.scrollTop;
        const elementTop = elementRect.top - containerRect.top + scrollTop;

        scrollContainerRef.current.scrollTo({
          top: elementTop - 20, // 20px offset from top
          behavior: "smooth",
        });

        // Clear article ID from hash after scrolling
        clearNewsArticleIdFromHash();
        articleIdRef.current = null;
      }
    };

    // Try immediately, then retry after a short delay to ensure items are rendered
    scrollToArticle();
    const timeoutId = setTimeout(scrollToArticle, 500);
    return () => clearTimeout(timeoutId);
  }, [displayedItems]);

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
    <div className="flex flex-col gap-2 mt-2">
      {/* Category filters for non-trending feeds */}
      {!isTrendingFeed ? (
        <NewsCategoryFilterBar
          feed={feed}
          selected={categories}
          onChange={onCategoriesChange}
          onClear={onClearCategories}
          className="mt-1"
        />
      ) : null}

      {/* News list */}
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
      <div className="mt-2 space-y-4">
        <p className="px-1 text-xs text-muted-foreground">
          Je opgeslagen artikelen worden lokaal op dit apparaat bewaard en worden niet
          gesynchroniseerd met andere apparaten.
        </p>
        <div className="rounded-2xl border border-border/80 bg-card p-6 text-center text-foreground shadow-soft">
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
    <div className="mt-2 space-y-4">
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


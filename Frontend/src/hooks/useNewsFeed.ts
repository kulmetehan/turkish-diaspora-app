import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchNews, type NewsItem } from "@/api/news";

type NewsFeedCacheEntry = {
  items: NewsItem[];
  total: number | null;
  timestamp: number;
};

const NEWS_FEED_CACHE = new Map<string, NewsFeedCacheEntry>();
const CACHE_TTL_MS = 60_000;
export const NEWS_FEED_STALE_MS = 120_000;

function createCacheKey(
  feed: string,
  pageSize: number,
  categoriesKey: string,
  citiesKey: string,
  trendCountryKey: string,
) {
  return `${feed}:${trendCountryKey}:${pageSize}:${categoriesKey}:${citiesKey}`;
}

export interface UseNewsFeedOptions {
  feed?: string;
  pageSize?: number;
  categories?: string[];
  citiesNl?: string[];
  citiesTr?: string[];
  trendCountry?: "nl" | "tr";
}

export interface UseNewsFeedResult {
  items: NewsItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  reload: () => Promise<void> | void;
  loadMore: () => void;
  isReloading: boolean;
  lastUpdatedAt: Date | null;
  meta?: {
    unavailable_reason?: string;
  };
}

export function useNewsFeed({
  feed = "diaspora",
  pageSize = 20,
  categories,
  citiesNl,
  citiesTr,
  trendCountry = "nl",
}: UseNewsFeedOptions = {}): UseNewsFeedResult {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [isReloading, setIsReloading] = useState<boolean>(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [meta, setMeta] = useState<{ unavailable_reason?: string } | undefined>(undefined);

  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const normalizedCategories = useMemo(() => {
    if (!categories || !categories.length) return [];
    return [...categories].map(c => c.trim().toLowerCase()).filter(Boolean).sort();
  }, [categories]);
  const categoriesKey = useMemo(() => {
    if (!normalizedCategories.length) return "";
    return normalizedCategories.join(",");
  }, [normalizedCategories]);
  const citiesKey = useMemo(() => {
    const nl = (citiesNl ?? []).map((city) => city.trim().toLowerCase()).filter(Boolean);
    const tr = (citiesTr ?? []).map((city) => city.trim().toLowerCase()).filter(Boolean);
    if (!nl.length && !tr.length) return "";
    return `${nl.sort().join(",")}|${tr.sort().join(",")}`;
  }, [citiesNl, citiesTr]);
  const trendCountryKey = feed === "trending" ? trendCountry : "";
  const cacheKey = createCacheKey(feed, pageSize, categoriesKey, citiesKey, trendCountryKey);

  const hasMore = useMemo(() => {
    if (total === null) return false;
    return items.length < total;
  }, [items.length, total]);

  const beginFetch = useCallback(
    async (
      nextOffset: number,
      append: boolean,
      options?: { force?: boolean; preserveItems?: boolean },
    ) => {
      requestIdRef.current += 1;
      const requestId = requestIdRef.current;
      const isInitialPage = !append && nextOffset === 0;

      if (isInitialPage && options?.force) {
        NEWS_FEED_CACHE.delete(cacheKey);
      }

      if (isInitialPage) {
        const cached = NEWS_FEED_CACHE.get(cacheKey);
        const now = Date.now();
        if (!options?.force && cached && now - cached.timestamp < CACHE_TTL_MS) {
          setTotal(cached.total);
          setItems(cached.items);
          setOffset(cached.items.length);
          setError(null);
          setIsLoading(false);
          setIsLoadingMore(false);
          setIsReloading(false);
          setLastUpdatedAt(new Date(cached.timestamp));
          return;
        }
      }

      if (append) {
        setIsLoadingMore(true);
      } else if (options?.preserveItems) {
        setIsReloading(true);
        setError(null);
      } else {
        setIsLoading(true);
        setError(null);
      }

      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      const controller = new AbortController();
      controllerRef.current = controller;

      try {
        const response = await fetchNews({
          feed,
          limit: pageSize,
          offset: nextOffset,
          categories: normalizedCategories.length ? normalizedCategories : undefined,
          citiesNl: citiesNl && citiesNl.length ? citiesNl : undefined,
          citiesTr: citiesTr && citiesTr.length ? citiesTr : undefined,
          trendCountry: feed === "trending" ? trendCountry : undefined,
          signal: controller.signal,
        });

        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          if (append) {
            setIsLoadingMore(false);
          } else if (options?.preserveItems) {
            setIsReloading(false);
          } else {
            setIsLoading(false);
          }
          return;
        }

        setTotal(response.total);
        setMeta(response.meta);

        setItems((prev) => {
          if (append) {
            return [...prev, ...response.items];
          }
          return response.items;
        });

        const now = Date.now();

        if (isInitialPage) {
          NEWS_FEED_CACHE.set(cacheKey, {
            items: response.items,
            total: response.total,
            timestamp: now,
          });
        }

        setOffset(nextOffset + response.items.length);
        setLastUpdatedAt(new Date(now));
      } catch (err) {
        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }
        const message =
          err instanceof Error
            ? err.message
            : "Er ging iets mis bij het laden van nieuws.";
        setError(message);
      } finally {
        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }
        if (append) {
          setIsLoadingMore(false);
        } else {
          if (options?.preserveItems) {
            setIsReloading(false);
          } else {
            setIsLoading(false);
          }
        }
      }
    },
    [cacheKey, feed, normalizedCategories, pageSize, citiesNl, citiesTr, trendCountry],
  );

  useEffect(() => {
    setItems([]);
    setTotal(null);
    setOffset(0);
    setError(null);
    setLastUpdatedAt(null);
    setMeta(undefined);

    void beginFetch(0, false);

    return () => {
      controllerRef.current?.abort();
    };
  }, [beginFetch]);

  const reload = useCallback(() => {
    if (isLoading || isReloading) {
      return;
    }
    return beginFetch(0, false, { force: true, preserveItems: true });
  }, [beginFetch, isLoading, isReloading]);

  const loadMore = useCallback(() => {
    if (isLoading || isLoadingMore || isReloading || !hasMore) {
      return;
    }
    void beginFetch(offset, true);
  }, [beginFetch, hasMore, isLoading, isLoadingMore, isReloading, offset]);

  return {
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
  };
}

export function clearNewsFeedCache() {
  NEWS_FEED_CACHE.clear();
}


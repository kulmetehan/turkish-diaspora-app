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

function createCacheKey(feed: string, pageSize: number, themesKey: string) {
  return `${feed}:${pageSize}:${themesKey}`;
}

function normalizeThemes(themes?: string[]): string[] {
  if (!themes || !themes.length) {
    return [];
  }

  const seen = new Set<string>();
  const result: string[] = [];

  for (const raw of themes) {
    if (!raw) continue;
    const normalized = raw.trim().toLowerCase();
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }

  return result;
}

export interface UseNewsFeedOptions {
  feed?: string;
  pageSize?: number;
  themes?: string[];
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
}

export function useNewsFeed({
  feed = "diaspora",
  pageSize = 20,
  themes,
}: UseNewsFeedOptions = {}): UseNewsFeedResult {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [isReloading, setIsReloading] = useState<boolean>(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);

  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const normalizedThemes = useMemo(() => normalizeThemes(themes), [themes]);
  const themesKey = useMemo(() => {
    if (!normalizedThemes.length) return "";
    return [...normalizedThemes].sort().join(",");
  }, [normalizedThemes]);
  const cacheKey = createCacheKey(feed, pageSize, themesKey);

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
          themes: normalizedThemes.length ? normalizedThemes : undefined,
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
    [cacheKey, feed, normalizedThemes, pageSize],
  );

  useEffect(() => {
    setItems([]);
    setTotal(null);
    setOffset(0);
    setError(null);
    setLastUpdatedAt(null);

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
  };
}

export function clearNewsFeedCache() {
  NEWS_FEED_CACHE.clear();
}


import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchNewsSearch, type NewsItem } from "@/api/news";

export interface UseNewsSearchOptions {
  query: string;
  pageSize?: number;
  debounceMs?: number;
  minLength?: number;
}

export interface UseNewsSearchResult {
  items: NewsItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  reload: () => void;
  loadMore: () => void;
}

const DEFAULT_DEBOUNCE_MS = 350;
const DEFAULT_MIN_LENGTH = 2;

export function useNewsSearch({
  query,
  pageSize = 20,
  debounceMs = DEFAULT_DEBOUNCE_MS,
  minLength = DEFAULT_MIN_LENGTH,
}: UseNewsSearchOptions): UseNewsSearchResult {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState<number>(0);
  const [reloadToken, setReloadToken] = useState<number>(0);
  const [debouncedQuery, setDebouncedQuery] = useState<string>("");

  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, debounceMs);
    return () => {
      window.clearTimeout(handle);
    };
  }, [query, debounceMs]);

  const hasValidQuery = debouncedQuery.length >= minLength;

  const beginFetch = useCallback(
    async (nextOffset: number, append: boolean) => {
      if (!hasValidQuery) {
        return;
      }

      requestIdRef.current += 1;
      const requestId = requestIdRef.current;

      if (append) {
        setIsLoadingMore(true);
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
        const response = await fetchNewsSearch({
          q: debouncedQuery,
          limit: pageSize,
          offset: nextOffset,
          signal: controller.signal,
        });

        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }

        setTotal(response.total);
        setItems((prev) => {
          if (append) {
            return [...prev, ...response.items];
          }
          return response.items;
        });
        setOffset(nextOffset + response.items.length);
      } catch (err) {
        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }
        const message =
          err instanceof Error
            ? err.message
            : "Er ging iets mis bij het zoeken.";
        setError(message);
      } finally {
        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }
        if (append) {
          setIsLoadingMore(false);
        } else {
          setIsLoading(false);
        }
      }
    },
    [debouncedQuery, hasValidQuery, pageSize],
  );

  useEffect(() => {
    setItems([]);
    setTotal(null);
    setOffset(0);
    setError(null);

    controllerRef.current?.abort();

    if (!hasValidQuery) {
      setIsLoading(false);
      setIsLoadingMore(false);
      return;
    }

    beginFetch(0, false);

    return () => {
      controllerRef.current?.abort();
    };
  }, [beginFetch, hasValidQuery, reloadToken]);

  const hasMore = useMemo(() => {
    if (total === null) return false;
    return items.length < total;
  }, [items.length, total]);

  const loadMore = useCallback(() => {
    if (!hasValidQuery || isLoading || isLoadingMore || !hasMore) {
      return;
    }
    beginFetch(offset, true);
  }, [beginFetch, hasMore, hasValidQuery, isLoading, isLoadingMore, offset]);

  const reload = useCallback(() => {
    if (!hasValidQuery) {
      return;
    }
    setReloadToken((token) => token + 1);
  }, [hasValidQuery]);

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  return {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    loadMore,
    reload,
  };
}

export default useNewsSearch;





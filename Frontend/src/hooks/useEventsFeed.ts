import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchEvents, type EventItem } from "@/api/events";

export interface UseEventsFeedOptions {
  pageSize?: number;
  city?: string;
  categories?: string[];
}

export interface UseEventsFeedResult {
  items: EventItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  reload: () => void;
  loadMore: () => void;
}

function normalizeCity(city?: string): string | undefined {
  if (!city) return undefined;
  const normalized = city.trim().toLowerCase().replace(/\s+/g, "_");
  return normalized || undefined;
}

function normalizeCategories(categories?: string[]): string[] | undefined {
  if (!categories || !categories.length) {
    return undefined;
  }
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of categories) {
    if (!raw) continue;
    const normalized = raw.trim().toLowerCase().replace(/\s+/g, "_");
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }
  return result.length ? result : undefined;
}

export function useEventsFeed({
  pageSize = 20,
  city,
  categories,
}: UseEventsFeedOptions = {}): UseEventsFeedResult {
  const [items, setItems] = useState<EventItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [reloadToken, setReloadToken] = useState(0);

  const controllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  const normalizedCity = useMemo(() => normalizeCity(city), [city]);
  const normalizedCategories = useMemo(
    () => normalizeCategories(categories),
    [categories],
  );

  const hasMore = useMemo(() => {
    if (total === null) return false;
    return items.length < total;
  }, [items.length, total]);

  const beginFetch = useCallback(
    async (nextOffset: number, append: boolean) => {
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
        const response = await fetchEvents({
          limit: pageSize,
          offset: nextOffset,
          city: normalizedCity,
          categories: normalizedCategories,
          signal: controller.signal,
        });

        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }

        setTotal(response.total);
        setItems((prev) => (append ? [...prev, ...response.items] : response.items));
        setOffset(nextOffset + response.items.length);
      } catch (err) {
        if (controller.signal.aborted || requestId !== requestIdRef.current) {
          return;
        }
        const message =
          err instanceof Error
            ? err.message
            : "Er ging iets mis bij het laden van events.";
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
    [normalizedCategories, normalizedCity, pageSize],
  );

  useEffect(() => {
    setItems([]);
    setTotal(null);
    setOffset(0);
    setError(null);
    beginFetch(0, false);

    return () => {
      controllerRef.current?.abort();
    };
  }, [beginFetch, reloadToken]);

  const reload = useCallback(() => {
    setReloadToken((token) => token + 1);
  }, []);

  const loadMore = useCallback(() => {
    if (isLoading || isLoadingMore || !hasMore) {
      return;
    }
    beginFetch(offset, true);
  }, [beginFetch, hasMore, isLoading, isLoadingMore, offset]);

  return {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    reload,
    loadMore,
  };
}



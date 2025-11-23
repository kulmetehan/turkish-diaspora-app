import { useCallback, useEffect, useMemo, useState } from "react";

import type { NewsItem } from "@/api/news";
import {
  capBookmarkCount,
  loadAndCleanupNewsBookmarks,
  pruneOldBookmarks,
  saveNewsBookmarks,
  type StoredNewsBookmark,
} from "@/lib/newsBookmarksStorage";

export interface UseNewsBookmarksResult {
  bookmarks: NewsItem[];
  isBookmarked: (id: number) => boolean;
  toggleBookmark: (item: NewsItem) => void;
  clearAll: () => void;
}

export function useNewsBookmarks(): UseNewsBookmarksResult {
  const [storedBookmarks, setStoredBookmarks] = useState<StoredNewsBookmark[]>(() =>
    loadAndCleanupNewsBookmarks(),
  );

  useEffect(() => {
    saveNewsBookmarks(storedBookmarks);
  }, [storedBookmarks]);

  const bookmarks = useMemo(() => storedBookmarks.map((entry) => entry.item), [storedBookmarks]);

  const bookmarkedIds = useMemo(() => {
    const ids = new Set<number>();
    for (const entry of storedBookmarks) {
      ids.add(entry.id);
    }
    return ids;
  }, [storedBookmarks]);

  const isBookmarked = useCallback((id: number) => bookmarkedIds.has(id), [bookmarkedIds]);

  const toggleBookmark = useCallback(
    (item: NewsItem) => {
      setStoredBookmarks((current) => {
        const exists = current.some((entry) => entry.id === item.id);
        if (exists) {
          const next = current.filter((entry) => entry.id !== item.id);
          return capBookmarkCount(pruneOldBookmarks(next));
        }

        const nextEntry: StoredNewsBookmark = {
          id: item.id,
          item,
          savedAt: new Date().toISOString(),
        };

        const next = [nextEntry, ...current.filter((entry) => entry.id !== item.id)];
        return capBookmarkCount(pruneOldBookmarks(next));
      });
    },
    [],
  );

  const clearAll = useCallback(() => {
    setStoredBookmarks([]);
  }, []);

  return {
    bookmarks,
    isBookmarked,
    toggleBookmark,
    clearAll,
  };
}

export default useNewsBookmarks;




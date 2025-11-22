import type { NewsItem } from "@/api/news";

const STORAGE_KEY = "tda_news_bookmarks_v1";
export const NEWS_BOOKMARKS_STORAGE_KEY = STORAGE_KEY;
const DAY_IN_MS = 86_400_000;

export interface StoredNewsBookmark {
  id: number;
  item: NewsItem;
  savedAt: string;
}

function isValidNewsItem(value: unknown): value is NewsItem {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<NewsItem>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.title === "string" &&
    typeof candidate.source === "string" &&
    typeof candidate.published_at === "string" &&
    typeof candidate.url === "string" &&
    Array.isArray(candidate.tags)
  );
}

function isStoredBookmark(value: unknown): value is StoredNewsBookmark {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<StoredNewsBookmark>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.savedAt === "string" &&
    isValidNewsItem(candidate.item)
  );
}

function sortBookmarks(entries: StoredNewsBookmark[]): StoredNewsBookmark[] {
  return [...entries].sort((a, b) => {
    const aTime = Date.parse(a.savedAt);
    const bTime = Date.parse(b.savedAt);
    if (Number.isNaN(aTime) && Number.isNaN(bTime)) return 0;
    if (Number.isNaN(aTime)) return 1;
    if (Number.isNaN(bTime)) return -1;
    return bTime - aTime;
  });
}

export function loadNewsBookmarks(): StoredNewsBookmark[] {
  if (typeof window === "undefined" || typeof window.localStorage === "undefined") {
    return [];
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return [];
    }

    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      return [];
    }

    const valid: StoredNewsBookmark[] = [];
    for (const entry of parsed) {
      if (!isStoredBookmark(entry)) {
        continue;
      }
      valid.push(entry);
    }
    return sortBookmarks(valid);
  } catch (error) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn("Failed to load news bookmarks from localStorage:", error);
    }
    return [];
  }
}

export function saveNewsBookmarks(entries: StoredNewsBookmark[]): void {
  if (typeof window === "undefined" || typeof window.localStorage === "undefined") {
    return;
  }

  try {
    const serialized = JSON.stringify(sortBookmarks(entries));
    window.localStorage.setItem(STORAGE_KEY, serialized);
  } catch (error) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn("Failed to save news bookmarks to localStorage:", error);
    }
  }
}

export function pruneOldBookmarks(
  entries: StoredNewsBookmark[],
  maxAgeDays = 90,
): StoredNewsBookmark[] {
  if (maxAgeDays <= 0) {
    return entries;
  }

  const cutoff = Date.now() - maxAgeDays * DAY_IN_MS;
  return entries.filter((entry) => {
    const timestamp = Date.parse(entry.savedAt);
    if (Number.isNaN(timestamp)) {
      return true;
    }
    return timestamp >= cutoff;
  });
}

export function capBookmarkCount(
  entries: StoredNewsBookmark[],
  maxEntries = 200,
): StoredNewsBookmark[] {
  if (maxEntries <= 0) {
    return [];
  }
  const sorted = sortBookmarks(entries);
  if (sorted.length <= maxEntries) {
    return sorted;
  }
  return sorted.slice(0, maxEntries);
}

export function loadAndCleanupNewsBookmarks(): StoredNewsBookmark[] {
  const loaded = loadNewsBookmarks();
  const pruned = pruneOldBookmarks(loaded);
  const capped = capBookmarkCount(pruned);

  const changed =
    loaded.length !== capped.length ||
    loaded.some((entry, index) => {
      const target = capped[index];
      if (!target) return true;
      return entry.id !== target.id || entry.savedAt !== target.savedAt;
    });

  if (changed) {
    saveNewsBookmarks(capped);
  }

  return capped;
}



import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { NewsItem } from "@/api/news";
import {
  NEWS_BOOKMARKS_STORAGE_KEY,
  saveNewsBookmarks,
  type StoredNewsBookmark,
} from "@/lib/newsBookmarksStorage";

import { useNewsBookmarks } from "@/hooks/useNewsBookmarks";

const SAMPLE_ITEM: NewsItem = {
  id: 99,
  title: "Bewaar dit artikel",
  source: "Test",
  published_at: "2025-11-22T10:00:00.000Z",
  url: "https://example.com/save",
  tags: ["bookmark"],
};

function bookmarkEntry(overrides: Partial<StoredNewsBookmark> = {}): StoredNewsBookmark {
  return {
    id: overrides.id ?? SAMPLE_ITEM.id,
    item: overrides.item ?? SAMPLE_ITEM,
    savedAt: overrides.savedAt ?? new Date().toISOString(),
  };
}

describe("useNewsBookmarks", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("initialises state from persisted bookmarks", async () => {
    const existing = bookmarkEntry({ id: 10, item: { ...SAMPLE_ITEM, id: 10 } });
    window.localStorage.setItem(NEWS_BOOKMARKS_STORAGE_KEY, JSON.stringify([existing]));

    const { result } = renderHook(() => useNewsBookmarks());

    expect(result.current.bookmarks).toHaveLength(1);
    expect(result.current.isBookmarked(10)).toBe(true);
  });

  it("toggles bookmarks on and off", () => {
    const { result } = renderHook(() => useNewsBookmarks());

    act(() => {
      result.current.toggleBookmark(SAMPLE_ITEM);
    });
    expect(result.current.bookmarks).toHaveLength(1);
    expect(result.current.isBookmarked(SAMPLE_ITEM.id)).toBe(true);

    act(() => {
      result.current.toggleBookmark(SAMPLE_ITEM);
    });
    expect(result.current.bookmarks).toHaveLength(0);
    expect(result.current.isBookmarked(SAMPLE_ITEM.id)).toBe(false);
  });

  it("persists updates to localStorage", () => {
    const { result } = renderHook(() => useNewsBookmarks());

    act(() => {
      result.current.toggleBookmark(SAMPLE_ITEM);
    });

    const stored = window.localStorage.getItem(NEWS_BOOKMARKS_STORAGE_KEY);
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored ?? "[]");
    expect(parsed).toHaveLength(1);
    expect(parsed[0]?.id).toBe(SAMPLE_ITEM.id);
  });

  it("cleans up stale bookmarks on load", () => {
    const oldDate = new Date(Date.now() - 200 * 86_400_000).toISOString();
    const stale = bookmarkEntry({ id: 5, savedAt: oldDate });
    saveNewsBookmarks([stale]);

    const { result } = renderHook(() => useNewsBookmarks());
    expect(result.current.bookmarks).toHaveLength(0);
  });
});



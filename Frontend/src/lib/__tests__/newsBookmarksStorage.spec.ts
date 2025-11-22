import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NewsItem } from "@/api/news";
import {
    NEWS_BOOKMARKS_STORAGE_KEY,
    capBookmarkCount,
    loadAndCleanupNewsBookmarks,
    loadNewsBookmarks,
    pruneOldBookmarks,
    saveNewsBookmarks,
    type StoredNewsBookmark,
} from "@/lib/newsBookmarksStorage";

const SAMPLE_ITEM: NewsItem = {
    id: 1,
    title: "Test artikel",
    source: "Testbron",
    published_at: "2025-11-20T10:00:00.000Z",
    url: "https://example.com/news/1",
    tags: ["test"],
};

function createBookmark(
    overrides: Partial<StoredNewsBookmark> = {},
): StoredNewsBookmark {
    return {
        id: overrides.id ?? SAMPLE_ITEM.id,
        item: overrides.item ?? SAMPLE_ITEM,
        savedAt: overrides.savedAt ?? new Date().toISOString(),
    };
}

describe("newsBookmarksStorage", () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("returns an empty array when storage is empty", () => {
        expect(loadNewsBookmarks()).toEqual([]);
    });

    it("ignores invalid JSON payloads", () => {
        window.localStorage.setItem(NEWS_BOOKMARKS_STORAGE_KEY, "{invalid");
        expect(loadNewsBookmarks()).toEqual([]);
    });

    it("saves and loads bookmarks roundtrip", () => {
        const entries = [
            createBookmark({
                id: 10,
                item: { ...SAMPLE_ITEM, id: 10, title: "Andere" },
            }),
        ];
        saveNewsBookmarks(entries);
        expect(loadNewsBookmarks()).toEqual(entries);
    });

    it("prunes bookmarks older dan de maximale leeftijd", () => {
        const oldDate = new Date(Date.now() - 120 * 86_400_000).toISOString();
        const fresh = createBookmark({ id: 2 });
        const stale = createBookmark({ id: 3, savedAt: oldDate });

        expect(pruneOldBookmarks([fresh, stale], 90)).toEqual([fresh]);
    });

    it("caps the total amount of bookmarks", () => {
        const entries = Array.from({ length: 5 }).map((_, index) =>
            createBookmark({ id: index + 1, savedAt: new Date(Date.now() - index * 1000).toISOString() }),
        );

        const capped = capBookmarkCount(entries, 2);
        expect(capped).toHaveLength(2);
        expect(capped[0]?.id).toBe(1);
        expect(capped[1]?.id).toBe(2);
    });

    it("cleans up storage during loadAndCleanupNewsBookmarks", () => {
        const oldDate = new Date(Date.now() - 200 * 86_400_000).toISOString();
        const stale = createBookmark({ id: 4, savedAt: oldDate });
        const fresh = createBookmark({ id: 5 });
        window.localStorage.setItem(
            NEWS_BOOKMARKS_STORAGE_KEY,
            JSON.stringify([stale, fresh]),
        );

        const cleaned = loadAndCleanupNewsBookmarks();

        expect(cleaned).toEqual([fresh]);
        expect(window.localStorage.getItem(NEWS_BOOKMARKS_STORAGE_KEY)).toBe(
            JSON.stringify([fresh]),
        );
    });
});



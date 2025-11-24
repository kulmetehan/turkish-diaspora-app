import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

import type { NewsListResponse } from "@/api/news";
import { fetchNews } from "@/api/news";

import { clearNewsFeedCache, useNewsFeed } from "@/hooks/useNewsFeed";

vi.mock("@/api/news", () => ({
  fetchNews: vi.fn(),
}));

const mockFetchNews = fetchNews as unknown as Mock;

function createNewsResponse(
  overrides: Partial<NewsListResponse> = {},
): NewsListResponse {
  return {
    items: [
      {
        id: 1,
        title: "Sample",
        source: "Test",
        published_at: "2025-01-01T00:00:00.000Z",
        url: "https://example.com",
        tags: [],
      },
    ],
    total: 40,
    limit: 20,
    offset: 0,
    ...overrides,
  };
}

describe("useNewsFeed", () => {
  afterEach(() => {
    vi.clearAllMocks();
    clearNewsFeedCache();
    vi.useRealTimers();
  });

  it("reuses cached first-page data within the TTL", async () => {
    mockFetchNews.mockResolvedValueOnce(createNewsResponse());

    const { result, rerender } = renderHook(
      ({ feed }) => useNewsFeed({ feed, pageSize: 20 }),
      { initialProps: { feed: "diaspora" as const } },
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockFetchNews).toHaveBeenCalledTimes(1);

    mockFetchNews.mockResolvedValueOnce(
      createNewsResponse({
        items: [
          {
            id: 2,
            title: "Another",
            source: "NL",
            published_at: "2025-01-02T00:00:00.000Z",
            url: "https://example.com/2",
            tags: [],
          },
        ],
      }),
    );

    rerender({ feed: "nl" });
    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(2));

    mockFetchNews.mockClear();
    rerender({ feed: "diaspora" });

    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(result.current.items[0]?.title).toBe("Sample");
    expect(mockFetchNews).not.toHaveBeenCalled();
  });

  it("passes normalized themes to the fetcher and busts cache when themes change", async () => {
    mockFetchNews.mockResolvedValueOnce(createNewsResponse());

    const { rerender } = renderHook(
      ({ themes }) => useNewsFeed({ feed: "diaspora", pageSize: 20, themes }),
      { initialProps: { themes: ["Politics"] as string[] } },
    );

    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(1));
    expect(mockFetchNews).toHaveBeenLastCalledWith(
      expect.objectContaining({ themes: ["politics"] }),
    );

    mockFetchNews.mockResolvedValueOnce(
      createNewsResponse({
        items: [
          {
            id: 3,
            title: "Sports Update",
            source: "TR",
            published_at: "2025-01-03T00:00:00.000Z",
            url: "https://example.com/3",
            tags: [],
          },
        ],
      }),
    );

    rerender({ themes: ["economy", "politics"] });

    await waitFor(() => expect(mockFetchNews).toHaveBeenCalledTimes(2));
    expect(mockFetchNews).toHaveBeenLastCalledWith(
      expect.objectContaining({ themes: ["economy", "politics"] }),
    );
  });

  it("tracks freshness timestamps and reload bypasses cache", async () => {
    const firstLoad = new Date("2025-01-01T00:00:00.000Z");
    let mockNow = firstLoad.getTime();
    const dateSpy = vi.spyOn(Date, "now").mockImplementation(() => mockNow);

    mockFetchNews.mockResolvedValueOnce(createNewsResponse());

    const { result } = renderHook(() => useNewsFeed({ feed: "diaspora", pageSize: 20 }));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.lastUpdatedAt?.toISOString()).toBe(firstLoad.toISOString());
    expect(mockFetchNews).toHaveBeenCalledTimes(1);

    mockFetchNews.mockResolvedValueOnce(
      createNewsResponse({
        items: [
          {
            id: 2,
            title: "Reloaded",
            source: "NL",
            published_at: "2025-01-02T00:00:00.000Z",
            url: "https://example.com/reloaded",
            tags: [],
          },
        ],
      }),
    );

    const secondLoad = new Date("2025-01-01T00:02:00.000Z");
    mockNow = secondLoad.getTime();

    await act(async () => {
      await result.current.reload();
    });

    await waitFor(() => expect(result.current.isReloading).toBe(false));
    expect(result.current.items[0]?.id).toBe(2);
    expect(result.current.lastUpdatedAt?.toISOString()).toBe(secondLoad.toISOString());
    expect(mockFetchNews).toHaveBeenCalledTimes(2);
    dateSpy.mockRestore();
  });
});


import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { NewsListResponse } from "@/api/news";
import { fetchNewsSearch } from "@/api/news";

import { useNewsSearch } from "@/hooks/useNewsSearch";

vi.mock("@/api/news", () => ({
  fetchNewsSearch: vi.fn(),
}));

const mockFetchNewsSearch =
  fetchNewsSearch as unknown as ReturnType<typeof vi.fn>;

function createResponse(
  overrides: Partial<NewsListResponse> = {},
): NewsListResponse {
  return {
    items: [
      {
        id: 1,
        title: "Rotterdam diaspora nieuws",
        source: "Test",
        published_at: "2025-11-22T09:15:00.000Z",
        url: "https://example.com/rotterdam",
        tags: [],
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
    ...overrides,
  };
}

function sleep(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

describe("useNewsSearch", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("skips API calls when the query is shorter than the minimum length", async () => {
    const { result } = renderHook(() =>
      useNewsSearch({ query: "a", debounceMs: 10 }),
    );

    await waitFor(
      () => {
        expect(mockFetchNewsSearch).not.toHaveBeenCalled();
      },
      { timeout: 50 },
    );

    expect(mockFetchNewsSearch).not.toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.items).toHaveLength(0);
  });

  it("debounces calls and only requests the latest query", async () => {
    mockFetchNewsSearch.mockResolvedValue(createResponse());

    const { rerender } = renderHook(
      ({ query }) => useNewsSearch({ query, debounceMs: 10 }),
      { initialProps: { query: "" } },
    );

    rerender({ query: "r" });
    await sleep(5);

    rerender({ query: "ro" });
    await sleep(5);

    rerender({ query: "rotterdam" });
    await waitFor(() => {
      expect(mockFetchNewsSearch).toHaveBeenCalledTimes(1);
    });
    expect(mockFetchNewsSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        q: "rotterdam",
        limit: 20,
        offset: 0,
      }),
    );
  });

  it("supports pagination via loadMore", async () => {
    mockFetchNewsSearch
      .mockResolvedValueOnce(
        createResponse({
          items: [
            {
              id: 10,
              title: "Eerste batch",
              source: "Test",
              published_at: "2025-11-22T09:00:00.000Z",
              url: "https://example.com/1",
              tags: [],
            },
            {
              id: 11,
              title: "Tweede batch",
              source: "Test",
              published_at: "2025-11-22T09:05:00.000Z",
              url: "https://example.com/2",
              tags: [],
            },
          ],
          total: 4,
          limit: 2,
        }),
      )
      .mockResolvedValueOnce(
        createResponse({
          items: [
            {
              id: 12,
              title: "Derde batch",
              source: "Test",
              published_at: "2025-11-22T09:10:00.000Z",
              url: "https://example.com/3",
              tags: [],
            },
          ],
          total: 4,
          limit: 2,
          offset: 2,
        }),
      );

    const { result } = renderHook(() =>
      useNewsSearch({ query: "rotterdam", pageSize: 2, debounceMs: 10 }),
    );

    await waitFor(() => {
      expect(mockFetchNewsSearch).toHaveBeenCalledTimes(1);
    });

    result.current.loadMore();

    await waitFor(() => {
      expect(mockFetchNewsSearch).toHaveBeenCalledTimes(2);
    });

    expect(mockFetchNewsSearch).toHaveBeenLastCalledWith(
      expect.objectContaining({
        q: "rotterdam",
        limit: 2,
        offset: 2,
      }),
    );
  });

  it("ignores stale responses when the query changes quickly", async () => {
    let resolveFirst: ((value: NewsListResponse) => void) | null = null;
    let resolveSecond: ((value: NewsListResponse) => void) | null = null;

    const firstPromise = new Promise<NewsListResponse>((resolve) => {
      resolveFirst = resolve;
    });
    const secondPromise = new Promise<NewsListResponse>((resolve) => {
      resolveSecond = resolve;
    });

    mockFetchNewsSearch
      .mockReturnValueOnce(firstPromise)
      .mockReturnValueOnce(secondPromise);

    const { rerender, result } = renderHook(
      ({ query }) => useNewsSearch({ query, debounceMs: 10 }),
      { initialProps: { query: "rotterdam" } },
    );

    await waitFor(() => {
      expect(mockFetchNewsSearch).toHaveBeenCalledTimes(1);
    });

    rerender({ query: "ankara" });
    await waitFor(() => {
      expect(mockFetchNewsSearch).toHaveBeenCalledTimes(2);
    });

    resolveSecond?.(
      createResponse({
        items: [
          {
            id: 99,
            title: "Ankara nieuws",
            source: "Test",
            published_at: "2025-11-22T10:00:00.000Z",
            url: "https://example.com/ankara",
            tags: [],
          },
        ],
        total: 1,
      }),
    );

    await waitFor(() => {
      expect(result.current.items[0]?.title).toBe("Ankara nieuws");
    });

    resolveFirst?.(
      createResponse({
        items: [
          {
            id: 55,
            title: "Rotterdam oud",
            source: "Test",
            published_at: "2025-11-22T08:00:00.000Z",
            url: "https://example.com/rotterdam-old",
            tags: [],
          },
        ],
        total: 1,
      }),
    );

    await waitFor(() => {
      expect(result.current.items[0]?.title).toBe("Ankara nieuws");
    });
  });
});


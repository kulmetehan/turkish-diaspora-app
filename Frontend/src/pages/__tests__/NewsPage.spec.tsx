import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NewsItem } from "@/api/news";
import type { UseNewsBookmarksResult } from "@/hooks/useNewsBookmarks";
import type { UseNewsFeedResult } from "@/hooks/useNewsFeed";
import type { UseNewsSearchResult } from "@/hooks/useNewsSearch";
import type { NewsFeedKey } from "@/lib/routing/newsFeed";
import { NEWS_FEEDS } from "@/lib/routing/newsFeed";

import NewsPage from "@/pages/NewsPage";

const mockUseNewsFeed = vi.fn();
const mockUseNewsSearch = vi.fn();
const mockUseNewsBookmarks = vi.fn();

vi.mock("@/hooks/useNewsFeed", () => ({
  useNewsFeed: (...args: unknown[]) => mockUseNewsFeed(...args),
  NEWS_FEED_STALE_MS: 120_000,
}));

vi.mock("@/hooks/useNewsSearch", () => ({
  useNewsSearch: (...args: unknown[]) => mockUseNewsSearch(...args),
}));

vi.mock("@/hooks/useNewsBookmarks", () => ({
  useNewsBookmarks: (...args: unknown[]) => mockUseNewsBookmarks(...args),
}));

vi.mock("@/components/news/NewsFeedTabs", () => ({
  NewsFeedTabs: ({
    value,
    onChange,
  }: {
    value: NewsFeedKey;
    onChange: (next: NewsFeedKey) => void;
  }) => (
    <div role="tablist">
      {NEWS_FEEDS.map((feed) => (
        <button
          key={feed.key}
          role="tab"
          aria-selected={value === feed.key}
          data-state={value === feed.key ? "active" : "inactive"}
          onClick={() => onChange(feed.key)}
        >
          {feed.label}
        </button>
      ))}
    </div>
  ),
}));

vi.mock("@/components/news/NewsList", () => ({
  NewsList: ({
    items,
    onLoadMore,
    hasMore,
    isLoading,
    emptyMessage,
    isBookmarked,
    toggleBookmark,
  }: {
    items: NewsItem[];
    onLoadMore: () => void;
    hasMore: boolean;
    isLoading: boolean;
    emptyMessage?: string;
    isBookmarked?: (id: number) => boolean;
    toggleBookmark?: (item: NewsItem) => void;
  }) => (
    <div>
      <div data-testid="news-items">
        {items.length
          ? items.map((item) => (
              <p
                key={item.id}
                data-bookmarked={isBookmarked?.(item.id) ? "true" : "false"}
                onClick={() => toggleBookmark?.(item)}
              >
                {item.title}
              </p>
            ))
          : emptyMessage
            ? <span>{emptyMessage}</span>
            : null}
      </div>
      {hasMore && !isLoading ? (
        <button type="button" onClick={onLoadMore}>
          Meer laden
        </button>
      ) : null}
    </div>
  ),
}));

const SAMPLE_ARTICLE: NewsItem = {
  id: 42,
  title: "Nieuwe ondernemersvereniging in Den Haag",
  snippet: "De vereniging ondersteunt Turkse ondernemers met advies en workshops.",
  source: "Den Haag Vandaag",
  published_at: "2025-11-21T08:00:00.000Z",
  url: "https://example.com/articles/denhaag",
  tags: ["ondernemen", "den haag"],
};

function createHookState(
  overrides: Partial<UseNewsFeedResult> = {},
): UseNewsFeedResult {
  return {
    items: [SAMPLE_ARTICLE],
    isLoading: false,
    isLoadingMore: false,
    error: null,
    hasMore: true,
    reload: vi.fn(),
    loadMore: vi.fn(),
    isReloading: false,
    lastUpdatedAt: new Date("2025-01-01T00:00:00.000Z"),
    ...overrides,
  };
}

function createSearchState(
  overrides: Partial<UseNewsSearchResult> = {},
): UseNewsSearchResult {
  return {
    items: [],
    isLoading: false,
    isLoadingMore: false,
    error: null,
    hasMore: false,
    reload: vi.fn(),
    loadMore: vi.fn(),
    ...overrides,
  };
}

describe("NewsPage", () => {
  beforeEach(() => {
    window.location.hash = "#/news";
    mockUseNewsFeed.mockImplementation(() => createHookState());
    mockUseNewsSearch.mockImplementation(() => createSearchState());
    mockUseNewsBookmarks.mockImplementation(
      (): UseNewsBookmarksResult => ({
        bookmarks: [],
        isBookmarked: vi.fn().mockReturnValue(false),
        toggleBookmark: vi.fn(),
        clearAll: vi.fn(),
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.location.hash = "#/";
  });

  it("defaults to the Voor jou feed when hash query is missing", () => {
    render(<NewsPage />);

    expect(mockUseNewsFeed).toHaveBeenCalledWith(
      expect.objectContaining({ feed: "diaspora", pageSize: 20, themes: [] }),
    );
    expect(mockUseNewsSearch).toHaveBeenCalledWith(
      expect.objectContaining({ query: "", pageSize: 20 }),
    );
  });

  it("initializes feed from the hash query parameter", () => {
    window.location.hash = "#/news?feed=tr";
    render(<NewsPage />);

    expect(mockUseNewsFeed).toHaveBeenCalledWith(
      expect.objectContaining({ feed: "tr", themes: [] }),
    );
    const lastCall = mockUseNewsFeed.mock.calls.at(-1)?.[0] as Record<
      string,
      unknown
    >;
    expect(lastCall?.feed).toBe("tr");
  });

  it("updates hash and hook feed when selecting another tab", async () => {
    render(<NewsPage />);

    const [tab] = screen.getAllByRole("tab", { name: "Nederland" });
    fireEvent.click(tab);

    await waitFor(() => {
      expect(window.location.hash).toContain("feed=nl");
    });
    const lastCall = mockUseNewsFeed.mock.calls.at(-1)?.[0] as Record<
      string,
      unknown
    >;
    expect(lastCall?.feed).toBe("nl");
  });

  it("reacts to browser hashchange events", async () => {
    render(<NewsPage />);

    window.location.hash = "#/news?feed=geo";
    window.dispatchEvent(new HashChangeEvent("hashchange"));

    await waitFor(() => {
      expect(mockUseNewsFeed).toHaveBeenLastCalledWith(
        expect.objectContaining({ feed: "geo", themes: [] }),
      );
    });
  });

  it("initializes the search input from the hash query parameter", () => {
    window.location.hash = "#/news?q=ankara";
    render(<NewsPage />);

    const input = screen.getByPlaceholderText(/zoek in diaspora nieuws/i) as HTMLInputElement;
    expect(input.value).toBe("ankara");

    expect(mockUseNewsSearch).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "ankara" }),
    );
  });

  it("writes the search query to the hash when typing", async () => {
    render(<NewsPage />);

    const input = screen.getByPlaceholderText(/zoek in diaspora nieuws/i);
    fireEvent.change(input, { target: { value: "geo" } });

    await waitFor(() => {
      expect(window.location.hash).toContain("q=geo");
    });
  });

  it("initializes themes from the hash", () => {
    window.location.hash = "#/news?themes=politics,economy";
    render(<NewsPage />);

    expect(mockUseNewsFeed).toHaveBeenCalledWith(
      expect.objectContaining({ themes: ["politics", "economy"] }),
    );
    const checkbox = screen.getByRole("checkbox", { name: "Politiek" });
    expect(checkbox.getAttribute("aria-checked")).toBe("true");
  });

  it("updates hash and hook when toggling a theme chip", async () => {
    render(<NewsPage />);

    const politicsChip = screen.getByRole("checkbox", { name: "Politiek" });
    fireEvent.click(politicsChip);

    await waitFor(() => {
      expect(window.location.hash).toContain("themes=politics");
    });

    const lastCall = mockUseNewsFeed.mock.calls.at(-1)?.[0] as Record<
      string,
      unknown
    >;
    expect(lastCall?.themes).toEqual(["politics"]);
  });

  it("clears filters with the clear button", async () => {
    window.location.hash = "#/news?themes=religion";
    render(<NewsPage />);

    const clearButton = screen.getByRole("button", { name: "Filters wissen" });
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(window.location.hash).not.toContain("themes=");
    });

    const lastCall = mockUseNewsFeed.mock.calls.at(-1)?.[0] as Record<
      string,
      unknown
    >;
    expect(lastCall?.themes).toEqual([]);
  });

  it("suppresses theme chips for the trending feed", () => {
    window.location.hash = "#/news?feed=trending";
    render(<NewsPage />);

    expect(
      screen.queryByRole("checkbox", { name: "Politiek" }),
    ).toBeNull();
    expect(screen.queryByText(/thema filters/i)).toBeNull();
  });

  it("does not forward themes to the hook for the trending feed", () => {
    window.location.hash = "#/news?feed=trending&themes=politics,economy";
    render(<NewsPage />);

    expect(mockUseNewsFeed).toHaveBeenCalledWith(
      expect.objectContaining({
        feed: "trending",
        themes: undefined,
      }),
    );
  });

  it("switches to search mode when query length meets threshold", async () => {
    const searchLoadMore = vi.fn();
    mockUseNewsSearch.mockImplementation(() =>
      createSearchState({
        items: [
          {
            ...SAMPLE_ARTICLE,
            id: 999,
            title: "Zoekresultaat",
          },
        ],
        hasMore: true,
        loadMore: searchLoadMore,
      }),
    );

    render(<NewsPage />);

    const input = screen.getByPlaceholderText(/zoek in diaspora nieuws/i);
    fireEvent.change(input, { target: { value: "rotterdam" } });

    await waitFor(() => {
      expect(mockUseNewsSearch).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "rotterdam" }),
      );
    });

    expect(screen.getByText("Zoekresultaat")).toBeTruthy();
    expect(screen.queryByText(SAMPLE_ARTICLE.title)).toBeNull();

    const loadMoreButton = screen.getByRole("button", { name: "Meer laden" });
    fireEvent.click(loadMoreButton);
    expect(searchLoadMore).toHaveBeenCalled();
  });

  it("returns to feed mode after clearing the search field", async () => {
    render(<NewsPage />);

    const input = screen.getByPlaceholderText(/zoek in diaspora nieuws/i);
    fireEvent.change(input, { target: { value: "news" } });

    await waitFor(() => {
      expect(mockUseNewsSearch).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "news" }),
      );
    });

    const clearButton = screen.getByRole("button", { name: "Zoekveld wissen" });
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(mockUseNewsSearch).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "" }),
      );
      expect(window.location.hash).not.toContain("q=");
    });

    expect(screen.getByText(SAMPLE_ARTICLE.title)).toBeTruthy();
  });

  it("shows search-specific context and empty copy when no results are found", async () => {
    mockUseNewsSearch.mockImplementation(() =>
      createSearchState({
        items: [],
        isLoading: false,
        error: null,
        hasMore: false,
      }),
    );

    render(<NewsPage />);

    const input = screen.getByPlaceholderText(/zoek in diaspora nieuws/i);
    fireEvent.change(input, { target: { value: "zz" } });

    await waitFor(() => {
      expect(mockUseNewsSearch).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "zz" }),
      );
      expect(window.location.hash).toContain("q=zz");
    });

    expect(
      screen.getByText(/zoekresultaten binnen de diaspora-feed/i),
    ).toBeTruthy();
    expect(
      screen.getByText("Geen artikelen gevonden voor je zoekopdracht."),
    ).toBeTruthy();
  });

  it("renders the refresh toolbar and triggers manual reloads", () => {
    const reloadMock = vi.fn().mockResolvedValue(undefined);
    mockUseNewsFeed.mockImplementation(() =>
      createHookState({
        reload: reloadMock,
        lastUpdatedAt: new Date("2025-01-01T10:00:00.000Z"),
      }),
    );

    render(<NewsPage />);

    const refreshButton = screen.getByRole("button", { name: "Ververs nieuws" });
    fireEvent.click(refreshButton);
    expect(reloadMock).toHaveBeenCalled();
    expect(screen.getByText(/Laatst bijgewerkt:/i)).toBeTruthy();
  });

  it("includes an Opgeslagen tab that updates the hash", async () => {
    render(<NewsPage />);

    const bookmarksTab = screen.getByRole("tab", { name: "Opgeslagen" });
    fireEvent.click(bookmarksTab);

    await waitFor(() => {
      expect(window.location.hash).toContain("feed=bookmarks");
    });
  });

  it("renders bookmarks without hitting the remote feeds", () => {
    const bookmark = { ...SAMPLE_ARTICLE, id: 100, title: "Bewaar lokaal" };
    mockUseNewsBookmarks.mockImplementation(
      (): UseNewsBookmarksResult => ({
        bookmarks: [bookmark],
        isBookmarked: vi.fn().mockReturnValue(true),
        toggleBookmark: vi.fn(),
        clearAll: vi.fn(),
      }),
    );

    window.location.hash = "#/news?feed=bookmarks";
    render(<NewsPage />);

    expect(mockUseNewsFeed).not.toHaveBeenCalled();
    expect(mockUseNewsSearch).not.toHaveBeenCalled();
    expect(screen.getByText("Bewaar lokaal")).toBeTruthy();
    expect(
      screen.getByText(/Je opgeslagen artikelen worden lokaal/i),
    ).toBeTruthy();
  });

  it("shows the empty bookmarks state with helper copy", () => {
    mockUseNewsBookmarks.mockImplementation(
      (): UseNewsBookmarksResult => ({
        bookmarks: [],
        isBookmarked: vi.fn().mockReturnValue(false),
        toggleBookmark: vi.fn(),
        clearAll: vi.fn(),
      }),
    );

    window.location.hash = "#/news?feed=bookmarks";
    render(<NewsPage />);

    expect(
      screen.getByText("Nog geen opgeslagen artikelen"),
    ).toBeTruthy();
    expect(
      screen.getByText(/Gebruik het bookmark-icoon bij een nieuwsbericht/i),
    ).toBeTruthy();
  });
});


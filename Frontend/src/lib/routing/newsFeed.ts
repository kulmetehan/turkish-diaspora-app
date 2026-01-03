const FEED_KEY = "feed";
const SEARCH_KEY = "q";

export type NewsFeedKey =
  | "diaspora"
  | "nl"
  | "tr"
  | "local"
  | "origin"
  | "geo"
  | "trending"
  | "music"
  | "bookmarks";

export const NEWS_FEEDS: Array<{ key: NewsFeedKey; labelKey: string }> = [
  { key: "nl", labelKey: "news.feeds.nl" },
  { key: "tr", labelKey: "news.feeds.tr" },
  { key: "local", labelKey: "news.feeds.local" },
  { key: "origin", labelKey: "news.feeds.origin" },
  { key: "trending", labelKey: "news.feeds.trending" },
  // Note: "music" feed is only available in FeedPage, not NewsPage
  { key: "bookmarks", labelKey: "news.feeds.bookmarks" },
];

const ALLOWED_FEEDS = NEWS_FEEDS.map((feed) => feed.key);

export function normalizeNewsFeed(raw: string | null | undefined): NewsFeedKey {
  if (!raw) return "nl";
  return ALLOWED_FEEDS.includes(raw as NewsFeedKey)
    ? (raw as NewsFeedKey)
    : "nl";
}

function getHashSearch(): URLSearchParams {
  if (typeof window === "undefined") {
    return new URLSearchParams();
  }
  const hash = window.location.hash ?? "";
  const queryIndex = hash.indexOf("?");
  const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
  return new URLSearchParams(query);
}

function buildHash(params: URLSearchParams): string {
  if (typeof window === "undefined") {
    return "#/";
  }
  const base = window.location.hash.split("?")[0] || "#/";
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

function updateHashParams(mutator: (params: URLSearchParams) => void) {
  if (typeof window === "undefined") return;
  const params = getHashSearch();
  mutator(params);
  const nextHash = buildHash(params);
  if (window.location.hash === nextHash) return;
  window.location.hash = nextHash;
}

export function readNewsFeedFromHash(): NewsFeedKey {
  const params = getHashSearch();
  const raw = params.get(FEED_KEY);
  return normalizeNewsFeed(raw);
}

export function writeNewsFeedToHash(next: NewsFeedKey) {
  updateHashParams((params) => {
    params.set(FEED_KEY, next);
  });
}

export function subscribeToNewsFeedHashChange(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

export function readNewsSearchQueryFromHash(): string {
  const params = getHashSearch();
  const raw = params.get(SEARCH_KEY) ?? "";
  return raw.trim();
}

export function writeNewsSearchQueryToHash(next: string) {
  updateHashParams((params) => {
    const normalized = (next ?? "").trim();
    if (normalized) {
      params.set(SEARCH_KEY, normalized);
    } else {
      params.delete(SEARCH_KEY);
    }
  });
}

export function clearNewsSearchQueryFromHash() {
  updateHashParams((params) => {
    if (params.has(SEARCH_KEY)) {
      params.delete(SEARCH_KEY);
    }
  });
}

const ARTICLE_KEY = "article";

export function readNewsArticleIdFromHash(): number | null {
  const params = getHashSearch();
  const raw = params.get(ARTICLE_KEY);
  if (!raw) return null;
  const id = parseInt(raw, 10);
  return Number.isNaN(id) ? null : id;
}

export function writeNewsArticleIdToHash(articleId: number | null) {
  updateHashParams((params) => {
    if (articleId !== null) {
      params.set(ARTICLE_KEY, articleId.toString());
    } else {
      params.delete(ARTICLE_KEY);
    }
  });
}

export function clearNewsArticleIdFromHash() {
  updateHashParams((params) => {
    if (params.has(ARTICLE_KEY)) {
      params.delete(ARTICLE_KEY);
    }
  });
}


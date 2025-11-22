import { apiFetch } from "@/lib/api";

export interface NewsItem {
  id: number;
  title: string;
  snippet?: string | null;
  source: string;
  published_at: string;
  url: string;
  image_url?: string | null;
  tags: string[];
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface FetchNewsParams {
  feed?: string;
  limit?: number;
  offset?: number;
  themes?: string[];
  signal?: AbortSignal;
}

export async function fetchNews({
  feed = "diaspora",
  limit = 20,
  offset = 0,
  themes,
  signal,
}: FetchNewsParams = {}): Promise<NewsListResponse> {
  const params = new URLSearchParams();
  params.set("feed", feed);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (themes && themes.length) {
    for (const theme of themes) {
      const normalized = theme.trim().toLowerCase();
      if (!normalized) continue;
      params.append("themes", normalized);
    }
  }

  const query = params.toString();
  return apiFetch<NewsListResponse>(`/api/v1/news?${query}`, {
    method: "GET",
    signal,
  });
}

export interface FetchNewsSearchParams {
  q: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

export async function fetchNewsSearch({
  q,
  limit = 20,
  offset = 0,
  signal,
}: FetchNewsSearchParams): Promise<NewsListResponse> {
  const normalized = q?.trim() ?? "";
  const params = new URLSearchParams();
  params.set("q", normalized);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  return apiFetch<NewsListResponse>(`/api/v1/news/search?${params.toString()}`, {
    method: "GET",
    signal,
  });
}


import { apiFetch } from "@/lib/api";

import type { ReactionType } from "@/lib/api";

export interface NewsItem {
  id: number;
  title: string;
  snippet?: string | null;
  source: string;
  published_at: string;
  url: string;
  image_url?: string | null;
  tags: string[];
  reactions?: Record<ReactionType, number> | null;
  user_reaction?: ReactionType | null;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
  limit: number;
  offset: number;
  meta?: {
    unavailable_reason?: string;
  };
}

export interface FetchNewsParams {
  feed?: string;
  limit?: number;
  offset?: number;
  categories?: string[];
  citiesNl?: string[];
  citiesTr?: string[];
  trendCountry?: "nl" | "tr";
  signal?: AbortSignal;
}

export async function fetchNews({
  feed = "diaspora",
  limit = 20,
  offset = 0,
  categories,
  citiesNl,
  citiesTr,
  trendCountry,
  signal,
}: FetchNewsParams = {}): Promise<NewsListResponse> {
  const params = new URLSearchParams();
  params.set("feed", feed);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (categories && categories.length) {
    for (const category of categories) {
      const normalized = category.trim().toLowerCase();
      if (!normalized) continue;
      params.append("categories", normalized);
    }
  }
  if (citiesNl && citiesNl.length) {
    for (const city of citiesNl) {
      const normalized = city.trim().toLowerCase();
      if (!normalized) continue;
      params.append("cities_nl", normalized);
    }
  }
  if (citiesTr && citiesTr.length) {
    for (const city of citiesTr) {
      const normalized = city.trim().toLowerCase();
      if (!normalized) continue;
      params.append("cities_tr", normalized);
    }
  }
  if (trendCountry) {
    params.set("trend_country", trendCountry);
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

export type CountryCode = "nl" | "tr";

interface NewsCityRecordRaw {
  city_key: string;
  name: string;
  country: string;
  province?: string | null;
  parent_key?: string | null;
  population?: number | null;
  lat?: number | null;
  lng?: number | null;
  metadata?: Record<string, unknown> | null;
}

interface NewsCityListResponseRaw {
  cities: NewsCityRecordRaw[];
  defaults?: Record<string, string[]>;
}

export interface NewsCity {
  cityKey: string;
  name: string;
  country: CountryCode;
  province?: string | null;
  parentKey?: string | null;
  population?: number | null;
  lat?: number | null;
  lng?: number | null;
  metadata?: Record<string, unknown> | null;
  legacyKey?: string;
}

export interface NewsCityList {
  cities: NewsCity[];
  defaults: Partial<Record<CountryCode, string[]>>;
}

function normalizeCountryCode(value: string): CountryCode {
  return value?.trim().toLowerCase() === "tr" ? "tr" : "nl";
}

function normalizeCityRecord(raw: NewsCityRecordRaw): NewsCity | null {
  const cityKey = (raw.city_key || "").trim().toLowerCase();
  if (!cityKey) return null;
  const metadata = raw.metadata ?? undefined;
  const legacyValue =
    typeof metadata?.legacy_key === "string"
      ? metadata.legacy_key.trim().toLowerCase()
      : undefined;
  const parentKey = (raw.parent_key || "").trim().toLowerCase();

  return {
    cityKey,
    name: raw.name,
    country: normalizeCountryCode(raw.country),
    province: raw.province ?? undefined,
    parentKey: parentKey || undefined,
    population: typeof raw.population === "number" ? raw.population : undefined,
    lat: typeof raw.lat === "number" ? raw.lat : undefined,
    lng: typeof raw.lng === "number" ? raw.lng : undefined,
    metadata,
    legacyKey: legacyValue,
  };
}

function normalizeDefaults(raw?: Record<string, string[]>): Partial<Record<CountryCode, string[]>> {
  if (!raw) return {};
  const result: Partial<Record<CountryCode, string[]>> = {};
  (["nl", "tr"] as const).forEach((country) => {
    const entries = raw[country];
    if (Array.isArray(entries)) {
      result[country] = entries.map((value) => (value || "").trim().toLowerCase()).filter(Boolean);
    }
  });
  return result;
}

export async function fetchNewsCities(params?: { country?: CountryCode }): Promise<NewsCityList> {
  const query = new URLSearchParams();
  if (params?.country) {
    query.set("country", params.country);
  }
  const suffix = query.toString();
  const payload = await apiFetch<NewsCityListResponseRaw>(
    `/api/v1/news/cities${suffix ? `?${suffix}` : ""}`,
    {
      method: "GET",
    },
  );
  const cities = (payload.cities ?? [])
    .map(normalizeCityRecord)
    .filter((city): city is NewsCity => Boolean(city));
  return {
    cities,
    defaults: normalizeDefaults(payload.defaults),
  };
}

export interface SearchNewsCitiesParams {
  country?: CountryCode;
  q: string;
  limit?: number;
  signal?: AbortSignal;
}

export async function searchNewsCities({
  country,
  q,
  limit,
  signal,
}: SearchNewsCitiesParams): Promise<NewsCity[]> {
  const params = new URLSearchParams();
  if (country) {
    params.set("country", country);
  }
  params.set("q", q);
  if (typeof limit === "number") {
    params.set("limit", String(limit));
  }
  const payload = await apiFetch<NewsCityRecordRaw[]>(
    `/api/v1/news/cities/search?${params.toString()}`,
    {
      method: "GET",
      signal,
    },
  );
  return (payload ?? []).map(normalizeCityRecord).filter((city): city is NewsCity => Boolean(city));
}


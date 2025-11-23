import { apiFetch } from "@/lib/api";

/**
 * Mirrors Backend/app/models/events_public.EventItem.
 * Optional lat/lng fields are future-proofed for when the backend exposes coordinates.
 */
export interface EventItem {
  id: number;
  title: string;
  description?: string | null;
  start_time_utc: string;
  end_time_utc?: string | null;
  city_key?: string | null;
  category_key?: string | null;
  location_text?: string | null;
  url?: string | null;
  source_key: string;
  summary_ai?: string | null;
  updated_at: string;
  /** TODO(ES-0.8): backend to expose coordinates so markers can render. */
  lat?: number | null;
  lng?: number | null;
}

export interface EventsListResponse {
  items: EventItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface FetchEventsParams {
  city?: string;
  dateFrom?: string;
  dateTo?: string;
  categories?: string[];
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

function normalizeCategories(categories?: string[]): string[] | undefined {
  if (!categories || !categories.length) {
    return undefined;
  }
  const unique = new Set<string>();
  const result: string[] = [];
  for (const raw of categories) {
    if (!raw) continue;
    const normalized = raw.trim().toLowerCase().replace(/\s+/g, "_");
    if (!normalized || unique.has(normalized)) continue;
    unique.add(normalized);
    result.push(normalized);
  }
  return result.length ? result : undefined;
}

export async function fetchEvents({
  city,
  dateFrom,
  dateTo,
  categories,
  limit = 20,
  offset = 0,
  signal,
}: FetchEventsParams = {}): Promise<EventsListResponse> {
  const params = new URLSearchParams();
  if (city) {
    params.set("city", city.trim().toLowerCase().replace(/\s+/g, "_"));
  }
  if (dateFrom) {
    params.set("date_from", dateFrom);
  }
  if (dateTo) {
    params.set("date_to", dateTo);
  }
  const normalizedCategories = normalizeCategories(categories);
  if (normalizedCategories) {
    for (const cat of normalizedCategories) {
      params.append("categories", cat);
    }
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const query = params.toString();
  return apiFetch<EventsListResponse>(`/api/v1/events${query ? `?${query}` : ""}`, {
    method: "GET",
    signal,
  });
}



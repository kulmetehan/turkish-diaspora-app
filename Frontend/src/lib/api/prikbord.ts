// Frontend/src/lib/api/prikbord.ts
import { authFetch, apiFetch } from "../api";
import type {
  SharedLink,
  SharedLinkCreate,
  SharedLinkFilters,
} from "@/types/prikbord";

export async function createSharedLink(
  data: SharedLinkCreate
): Promise<SharedLink> {
  return authFetch("/api/v1/prikbord/links", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getSharedLinks(
  filters?: SharedLinkFilters,
  limit: number = 50,
  offset: number = 0
): Promise<SharedLink[]> {
  const params = new URLSearchParams();
  if (filters?.platform) params.set("platform", filters.platform);
  if (filters?.city) params.set("city", filters.city);
  if (filters?.tags && filters.tags.length > 0) {
    params.set("tags", filters.tags.join(","));
  }
  if (filters?.post_type) params.set("post_type", filters.post_type);
  if (filters?.trending) params.set("trending", "true");
  if (filters?.search) params.set("search", filters.search);
  params.set("limit", limit.toString());
  params.set("offset", offset.toString());

  const query = params.toString();
  const path = `/api/v1/prikbord/links${query ? `?${query}` : ""}`;
  return apiFetch(path);
}

export async function getSharedLink(id: number): Promise<SharedLink> {
  return apiFetch(`/api/v1/prikbord/links/${id}`);
}

export async function likeSharedLink(
  id: number
): Promise<{ liked: boolean }> {
  return apiFetch(`/api/v1/prikbord/links/${id}/like`, {
    method: "POST",
  });
}

export async function bookmarkSharedLink(
  id: number
): Promise<{ bookmarked: boolean }> {
  return apiFetch(`/api/v1/prikbord/links/${id}/bookmark`, {
    method: "POST",
  });
}

export async function deleteSharedLink(
  id: number
): Promise<{ ok: boolean; message: string }> {
  return authFetch(`/api/v1/prikbord/links/${id}`, {
    method: "DELETE",
  });
}

export async function getTrendingLinks(
  limit: number = 20
): Promise<SharedLink[]> {
  const params = new URLSearchParams();
  params.set("limit", limit.toString());
  return apiFetch(`/api/v1/prikbord/links/trending?${params.toString()}`);
}

export async function toggleSharedLinkReaction(
  id: number,
  reactionType: string
): Promise<{ reaction_type: string; is_active: boolean; count: number }> {
  return apiFetch(`/api/v1/prikbord/links/${id}/reactions`, {
    method: "POST",
    body: JSON.stringify({ reaction_type: reactionType }),
  });
}

export async function getSharedLinkReactions(
  id: number
): Promise<{ reactions: Record<string, number>; user_reaction: string | null }> {
  return apiFetch(`/api/v1/prikbord/links/${id}/reactions`);
}

export async function getAvailablePlatforms(): Promise<string[]> {
  const response = await apiFetch<{ platforms: string[] }>("/api/v1/prikbord/platforms");
  return response.platforms;
}

export interface UrlPreviewData {
  title: string | null;
  description: string | null;
  image_url: string | null;
  domain: string;
}

export async function previewUrl(url: string): Promise<UrlPreviewData> {
  return apiFetch("/api/v1/prikbord/preview-url", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}


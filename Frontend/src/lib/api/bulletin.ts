// Frontend/src/lib/api/bulletin.ts
import { authFetch, apiFetch } from "../api";
import type { BulletinPost, BulletinPostCreate, BulletinPostFilters } from "@/types/bulletin";

export async function createBulletinPost(data: BulletinPostCreate): Promise<BulletinPost> {
  return authFetch("/api/v1/bulletin/posts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getBulletinPosts(
  filters?: BulletinPostFilters,
  limit: number = 50,
  offset: number = 0
): Promise<BulletinPost[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.city) params.set("city", filters.city);
  if (filters?.search) params.set("search", filters.search);
  params.set("limit", limit.toString());
  params.set("offset", offset.toString());

  const query = params.toString();
  const path = `/api/v1/bulletin/posts${query ? `?${query}` : ""}`;
  return apiFetch(path);
}

export async function getBulletinPost(id: number): Promise<BulletinPost> {
  return apiFetch(`/api/v1/bulletin/posts/${id}`);
}

export async function trackContactClick(postId: number): Promise<{ ok: boolean }> {
  return apiFetch(`/api/v1/bulletin/posts/${postId}/contact`, {
    method: "POST",
  });
}

export async function reportBulletinPost(
  postId: number,
  reason: string,
  details?: string
): Promise<{ ok: boolean; message: string }> {
  return apiFetch(`/api/v1/bulletin/posts/${postId}/report`, {
    method: "POST",
    body: JSON.stringify({ reason, details }),
  });
}

export async function deleteBulletinPost(postId: number): Promise<{ ok: boolean; message: string }> {
  return authFetch(`/api/v1/bulletin/posts/${postId}`, {
    method: "DELETE",
  });
}


// Frontend/src/lib/api/promotions.ts
import { apiFetch } from "../api";

export interface CreateLocationPromotionRequest {
  location_id: number;
  promotion_type: "trending" | "feed" | "both";
  duration_days: 7 | 14 | 30;
}

export interface CreateNewsPromotionRequest {
  title: string;
  content: string;
  url?: string;
  image_url?: string;
  duration_days: 7 | 14 | 30;
}

export interface PromotionResponse {
  id: number;
  promotion_type?: string;
  location_id?: number;
  title?: string;
  starts_at: string;
  ends_at: string;
  status: string;
  price_cents?: number;
  payment_intent_id?: string;
  client_secret?: string;
}

export interface LocationPromotion {
  id: number;
  location_id: number;
  location_name?: string;
  promotion_type: string;
  starts_at: string;
  ends_at: string;
  status: string;
  stripe_payment_intent_id?: string;
  created_at: string;
}

export interface NewsPromotion {
  id: number;
  title: string;
  content: string;
  url?: string;
  image_url?: string;
  starts_at: string;
  ends_at: string;
  status: string;
  stripe_payment_intent_id?: string;
  created_at: string;
}

export interface ClaimedLocation {
  id: number;
  name: string;
  address?: string;
  category?: string;
}

export async function createLocationPromotion(
  request: CreateLocationPromotionRequest
): Promise<PromotionResponse> {
  return apiFetch<PromotionResponse>("/api/v1/promotions/locations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

export async function createNewsPromotion(
  request: CreateNewsPromotionRequest
): Promise<PromotionResponse> {
  return apiFetch<PromotionResponse>("/api/v1/promotions/news", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

export async function listLocationPromotions(): Promise<LocationPromotion[]> {
  return apiFetch<LocationPromotion[]>("/api/v1/promotions/locations");
}

export async function listNewsPromotions(): Promise<NewsPromotion[]> {
  return apiFetch<NewsPromotion[]>("/api/v1/promotions/news");
}

export async function cancelLocationPromotion(
  promotionId: number
): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/api/v1/promotions/locations/${promotionId}`, {
    method: "DELETE",
  });
}

export async function cancelNewsPromotion(
  promotionId: number
): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/api/v1/promotions/news/${promotionId}`, {
    method: "DELETE",
  });
}

export async function getClaimedLocations(): Promise<ClaimedLocation[]> {
  return apiFetch<ClaimedLocation[]>("/api/v1/promotions/claimed-locations");
}
























// Frontend/src/types/prikbord.ts

export type Platform =
  | "marktplaats"
  | "instagram"
  | "facebook"
  | "youtube"
  | "twitter"
  | "tiktok"
  | "news"
  | "event"
  | "media"
  | "other";

export type ContextTag = "🏠" | "🛍️" | "🎉" | "📺";

export interface CreatorInfo {
  type: "user" | "business";
  id?: string;
  name?: string;
  avatar_url?: string | null;
  primary_role?: string | null;
  secondary_role?: string | null;
  verified?: boolean;
}

export interface SharedLink {
  id: number;
  url: string;
  platform: Platform;
  title: string | null;
  description: string | null;
  image_url: string | null;
  video_url: string | null;
  preview_method: string | null;
  creator: CreatorInfo;
  linked_location: {
    id: number;
    name: string;
    address?: string;
  } | null;
  city: string | null;
  neighborhood: string | null;
  context_tags: ContextTag[];
  media_urls: string[];
  post_type: "link" | "media" | "text";
  view_count: number;
  like_count: number;
  bookmark_count: number;
  is_liked: boolean;
  is_bookmarked: boolean;
  reactions?: Record<string, number> | null;
  user_reaction?: string | null;
  created_at: string;
  status: string;
}

export interface SharedLinkCreate {
  url?: string;
  linked_location_id?: number;
  city?: string;
  neighborhood?: string;
  context_tags?: ContextTag[];
  creator_type?: "user" | "business";
  business_id?: number;
  // Optional manual preview data (used when automatic preview fails)
  title?: string;
  description?: string;
  image_url?: string;
  // Media uploads support
  media_urls?: string[];
  post_type?: "link" | "media" | "text";
}

export interface SharedLinkFilters {
  platform?: Platform;
  city?: string;
  tags?: ContextTag[];
  post_type?: "link" | "media" | "text";
  trending?: boolean;
  search?: string;
}

export const CONTEXT_TAGS: { value: ContextTag; label: string }[] = [
  { value: "🏠", label: "Wonen" },
  { value: "🛍️", label: "Ondernemer" },
  { value: "🎉", label: "Event" },
  { value: "📺", label: "Media" },
];

export const PLATFORM_LABELS: Record<Platform, string> = {
  marktplaats: "Marktplaats",
  instagram: "Instagram",
  facebook: "Facebook",
  youtube: "YouTube",
  twitter: "Twitter/X",
  tiktok: "TikTok",
  news: "Nieuws",
  event: "Evenement",
  media: "Media",
  other: "Anders",
};


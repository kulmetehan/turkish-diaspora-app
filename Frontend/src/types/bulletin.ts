// Frontend/src/types/bulletin.ts

export type BulletinCategory = "personnel_wanted" | "offer" | "free_for_sale" | "event" | "services" | "other";

export type BulletinStatus = "pending" | "active" | "expired" | "removed" | "reported";

export type ModerationStatus = "pending" | "approved" | "rejected" | "requires_review" | "reported";

export interface CreatorInfo {
  type: "user" | "business" | "unknown";
  id?: string;
  name?: string;
  verified?: boolean;
}

export interface LinkedLocation {
  id: number;
  name: string;
  address?: string;
}

export interface ContactInfo {
  phone?: string;
  email?: string;
  whatsapp?: string;
}

export interface BulletinPost {
  id: number;
  title: string;
  description?: string;
  category: BulletinCategory;
  city?: string;
  neighborhood?: string;
  linked_location?: LinkedLocation;
  contact_info?: ContactInfo;
  image_urls: string[];
  creator: CreatorInfo;
  view_count: number;
  contact_count: number;
  created_at: string; // ISO datetime
  expires_at?: string; // ISO datetime
  status: BulletinStatus;
  moderation_status: ModerationStatus;
  moderation_message?: string;
}

export interface BulletinPostCreate {
  title: string;
  description?: string;
  category: BulletinCategory;
  creator_type: "user" | "business";
  business_id?: number;
  linked_location_id?: number;
  city?: string;
  neighborhood?: string;
  contact_phone?: string;
  contact_email?: string;
  contact_whatsapp?: string;
  show_contact_info: boolean;
  image_urls?: string[];
  expires_in_days?: number;
}

export interface BulletinPostFilters {
  status?: BulletinStatus | "all";
  category?: BulletinCategory;
  city?: string;
  search?: string;
}


/**
 * Event submission types and API client functions.
 */

export interface EventSubmissionCreate {
  title: string;
  description?: string;
  start_time_utc: string; // ISO 8601 datetime string
  end_time_utc?: string; // ISO 8601 datetime string
  location_text?: string;
  lat?: number;
  lng?: number;
  url?: string;
  category_key?: string;
}

export interface EventSubmissionResponse {
  id: number;
  title: string;
  description?: string | null;
  start_time_utc: string;
  end_time_utc?: string | null;
  location_text?: string | null;
  lat?: number | null;
  lng?: number | null;
  url?: string | null;
  category_key?: string | null;
  user_id: string;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  created_event_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface GeocodeResponse {
  lat: number;
  lng: number;
  display_name: string;
}


export interface Location {
  id: number;
  name: string;
  address?: string | null;
  lat: number;
  lng: number;
  category?: string | null;
  business_status?: string | null;
  rating?: number | null;
  user_ratings_total?: number | null;
  state?: string | null;
}

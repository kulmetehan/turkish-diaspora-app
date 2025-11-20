// Frontend/src/lib/map/marker-icons.tsx
// F4-S2: Snap-style category-based marker icons matching map design
import type { LocationMarker } from "@/api/fetchLocations";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  MARKER_BASE_SIZE,
  MARKER_FILL_DEFAULT,
  MARKER_ICON_COLOR,
  MARKER_BORDER_RADIUS,
  MARKER_ICON_SIZE,
  normalizeCategoryKey,
} from "@/lib/map/categoryIcons";
import {
  Utensils,
  ShoppingCart,
  Croissant,
  Beef,
  Scissors,
  Coffee,
  Building2,
  MapPin,
  CarFront,
  ShieldCheck,
  Needle,
  Plane,
  Sandwich,
  type LucideIcon,
} from "lucide-react";

type Props = { loc: LocationMarker; selected?: boolean };

/**
 * F4-S2: Map category key to Lucide icon component
 * Matches the mapping in categoryIcons.ts RAW_CATEGORY_CONFIG
 */
function getCategoryIcon(categoryKey: string | null | undefined): LucideIcon {
  const normalized = normalizeCategoryKey(categoryKey);
  switch (normalized) {
    case "restaurant":
      return Utensils;
    case "supermarket":
      return ShoppingCart;
    case "bakery":
      return Croissant;
    case "butcher":
      return Beef;
    case "barber":
    case "barbershop": // Alias handled by normalizeCategoryKey, but keep for safety
      return Scissors;
    case "cafe":
      return Coffee;
    case "mosque":
      return Building2;
    case "car_dealer":
      return CarFront;
    case "insurance":
      return ShieldCheck;
    case "tailor":
      return Needle;
    case "travel_agency":
      return Plane;
    case "fast_food":
      return Sandwich;
    default:
      return MapPin; // fallback
  }
}

/**
 * F4-S2: Snap-style marker icon component
 * Renders a red badge with white Lucide icon matching the map marker design
 */
export function MarkerIcon({ loc, selected }: Props) {
  // F4-S2: Use category instead of status for icon selection
  const categoryKey = loc.category_key ?? loc.category ?? null;
  const Icon = getCategoryIcon(categoryKey);

  // F4-S2: Use Snap-style design tokens
  const size = MARKER_BASE_SIZE; // 32px, can be scaled down for list context if needed
  const borderRadius = MARKER_BORDER_RADIUS;

  return (
    <div
      className={cn(
        "text-white shadow-lg border border-white/60",
        selected ? "ring-2 ring-black/20 scale-105" : "ring-1 ring-black/10",
        "transition-transform will-change-transform"
      )}
      style={{
        width: size,
        height: size,
        borderRadius: `${borderRadius}px`,
        backgroundColor: MARKER_FILL_DEFAULT,
        display: "grid",
        placeItems: "center",
      }}
    >
      <Icon size={MARKER_ICON_SIZE} color={MARKER_ICON_COLOR} strokeWidth={2} />
      <span className="sr-only">{loc.name}</span>
    </div>
  );
}

export function MarkerBadge({ loc }: { loc: LocationMarker }) {
  const tone =
    loc.state === "VERIFIED" ? "default" :
      loc.state === "PENDING_VERIFICATION" ? "secondary" : "outline";
  return <Badge variant={tone as any}>{loc.category}</Badge>;
}

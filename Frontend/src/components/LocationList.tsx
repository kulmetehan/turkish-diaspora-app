import { useEffect, useMemo, useRef } from "react";

import type { LocationMarker } from "@/api/fetchLocations";
import { Icon, type IconProps } from "@/components/Icon";
import { ShareButton } from "@/components/share/ShareButton";
import { humanizeCategoryLabel } from "@/lib/categories";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

type Props = {
  locations: LocationMarker[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
  onSelectDetail?: (id: string) => void;
  onShowOnMap?: (id: string) => void;
  autoScrollToSelected?: boolean;
  emptyText?: string; // Keep for backward compatibility, but may not be used
  fullHeight?: boolean;
  isLoading?: boolean; // NEW: global loading state
  error?: string | null; // NEW: global error state
  hasActiveSearch?: boolean; // NEW: whether there's an active search/filter
};

// Category icon mapping (matches CategoryChips)
const CATEGORY_ICON_MAP: Record<string, IconProps["name"]> = {
  restaurant: "UtensilsCrossed",
  bakery: "Croissant",
  supermarket: "ShoppingBasket",
  barber: "Scissors",
  mosque: "MoonStar",
  travel_agency: "Plane",
  butcher: "Beef",
  fast_food: "Sandwich",
  cafe: "Coffee",
  cafe_bar: "Beer",
  grocery: "ShoppingCart",
  sweets: "Candy",
  deli: "Sandwich",
  automotive: "CarFront",
  insurance: "ShieldCheck",
  tailor: "Spool",
  events_venue: "Calendar",
  community_centre: "Users",
  clinic: "HeartPulse",
  other: "Store",
};

function resolveIconName(categoryKey: string | null | undefined): IconProps["name"] {
  if (!categoryKey) return "Store";
  const normalized = categoryKey.toLowerCase();
  return CATEGORY_ICON_MAP[normalized] ?? "Store";
}

export default function LocationList({
  locations,
  selectedId,
  onSelect,
  onSelectDetail,
  onShowOnMap,
  autoScrollToSelected = true,
  emptyText: _legacyEmptyText,
  fullHeight = false,
  isLoading = false,
  error = null,
  hasActiveSearch = false,
}: Props) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Zorg dat onze refs altijd up-to-date zijn met de zichtbare lijst
  const ids = useMemo(() => locations.map((l) => l.id).join(","), [locations]);

  useEffect(() => {
    // Cleanup refs van items die niet meer bestaan
    const keep = new Set(locations.map((l) => l.id));
    for (const id of Array.from(itemRefs.current.keys())) {
      if (!keep.has(id)) itemRefs.current.delete(id);
    }
  }, [ids, locations]);

  // Auto-scroll naar geselecteerd item
  useEffect(() => {
    if (!autoScrollToSelected || !selectedId) return;
    const el = itemRefs.current.get(selectedId);
    if (!el) return;

    // Find the scrollable parent (should be the list container in MapTab)
    let scrollableParent: HTMLElement | null = el.parentElement;
    while (scrollableParent && scrollableParent !== document.body) {
      const style = window.getComputedStyle(scrollableParent);
      if (style.overflowY === "auto" || style.overflowY === "scroll" || style.overflow === "auto" || style.overflow === "scroll") {
        break;
      }
      scrollableParent = scrollableParent.parentElement;
    }

    if (!scrollableParent) return;

    const box = el.getBoundingClientRect();
    const cbox = scrollableParent.getBoundingClientRect();
    const outside = box.top < cbox.top || box.bottom > cbox.bottom;

    if (outside) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [selectedId, autoScrollToSelected]);

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-center text-muted-foreground shadow-soft">
        {t("location.list.warmingUp")}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-center text-foreground shadow-soft">
        {error || t("location.list.loadError")}
      </div>
    );
  }

  // Empty state - distinguish between search vs no data
  if (!locations.length) {
    const message = hasActiveSearch
      ? t("location.list.noSearchResults")
      : t("location.list.noLocationsInCity");
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-center text-muted-foreground shadow-soft">
        {message}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="space-y-3"
    >
      {locations.map((l) => {
        const active = l.id === selectedId;
        const categoryKey = l.category_key ?? l.category ?? null;
        const categoryIconName = resolveIconName(categoryKey);
        return (
          <div
            key={l.id}
            ref={(el) => {
              // callback-ref mag niets teruggeven:
              if (el) itemRefs.current.set(l.id, el);
              else itemRefs.current.delete(l.id);
            }}
            role="button"
            className={cn(
              "border border-border rounded-3xl bg-card shadow-soft p-4 transition-all duration-200 ease-out text-foreground",
              "hover:border-brand-accent hover:shadow-card",
              active
                ? "border-transparent bg-[hsl(var(--brand-red-strong))] text-brand-white shadow-[0_20px_35px_rgba(0,0,0,0.45)] ring-1 ring-brand-white/60"
                : ""
            )}
            onClick={() => onSelect?.(l.id)}
          >
            <div className="flex items-center gap-3">
              <Icon
                name={categoryIconName}
                className={cn(
                  "h-5 w-5 shrink-0",
                  active ? "text-brand-white" : "text-primary"
                )}
                aria-hidden
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-gilroy font-medium">{l.name}</div>
                <div className={cn(
                  "text-xs font-gilroy font-normal mt-1",
                  active ? "text-brand-white/80" : "text-muted-foreground"
                )}>
                  {humanizeCategoryLabel(l.category_label ?? l.category)}
                </div>
              </div>
              <div className="flex flex-row items-center gap-2 shrink-0">
                {onShowOnMap && (
                  <button
                    type="button"
                    className={cn(
                      "text-xs font-gilroy font-normal underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring whitespace-nowrap",
                      active ? "text-brand-white/80" : "text-muted-foreground"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onShowOnMap(l.id);
                    }}
                  >
                    Toon op kaart
                  </button>
                )}
                {onSelectDetail && (
                  <button
                    type="button"
                    className={cn(
                      "text-xs font-gilroy font-normal underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring whitespace-nowrap",
                      active ? "text-brand-white" : "text-primary"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectDetail(l.id);
                    }}
                  >
                    Details
                  </button>
                )}
                <div onClick={(e) => e.stopPropagation()}>
                  <ShareButton
                    location={{
                      id: l.id,
                      name: l.name,
                      category: l.category_label ?? l.category ?? null,
                    }}
                    size="sm"
                    variant="ghost"
                    className={cn(
                      "h-6 px-2",
                      active ? "text-brand-white hover:text-brand-white/80" : ""
                    )}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

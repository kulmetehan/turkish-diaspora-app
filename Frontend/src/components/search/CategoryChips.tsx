import { useCallback, useMemo, useRef, type KeyboardEvent } from "react";

import { Icon, type IconProps } from "@/components/Icon";
import { humanizeCategoryLabel } from "@/lib/categories";
import { cn } from "@/lib/utils";

type CategoryOption = {
  key: string;
  label?: string;
};

type CategoryChipsProps = {
  categories: CategoryOption[];
  activeCategory: string;
  onSelect: (key: string) => void;
};

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
  shop: "ShoppingBag",
  other: "Store",
};

function resolveIconName(key: string): IconProps["name"] {
  if (!key) return "Tag";
  return CATEGORY_ICON_MAP[key] ?? "Store";
}

export function CategoryChips({ categories, activeCategory, onSelect }: CategoryChipsProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const normalizedCategories = useMemo(() => {
    const unique = new Map<string, string>();
    for (const category of categories) {
      const key = category.key.toLowerCase();
      if (!key || unique.has(key)) continue;
      const label = category.label?.trim() || humanizeCategoryLabel(key);
      unique.set(key, label);
    }
    return Array.from(unique.entries()).map(([key, label]) => ({ key, label }));
  }, [categories]);

  const options = useMemo(
    () => [{ key: "all", label: "Alle" }, ...normalizedCategories],
    [normalizedCategories],
  );

  const handleArrowNavigation = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") {
      return;
    }
    const container = containerRef.current;
    if (!container) return;
    const buttons = Array.from(container.querySelectorAll<HTMLButtonElement>('button[role="option"]'));
    if (!buttons.length) return;
    const activeElement = document.activeElement as HTMLButtonElement | null;
    const currentIndex = activeElement ? buttons.indexOf(activeElement) : -1;

    let targetIndex = currentIndex;
    if (currentIndex === -1) {
      targetIndex = 0;
    } else if (event.key === "ArrowRight") {
      targetIndex = Math.min(currentIndex + 1, buttons.length - 1);
    } else if (event.key === "ArrowLeft") {
      targetIndex = Math.max(currentIndex - 1, 0);
    }

    const target = buttons[targetIndex];
    if (target && target !== activeElement) {
      event.preventDefault();
      target.focus();
      target.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, []);

  return (
    <div className="relative">
      <div
        ref={containerRef}
        role="listbox"
        aria-label="Filter op categorie"
        className={cn(
          "pointer-events-auto -mx-1 flex items-center gap-2 overflow-x-auto px-1 pb-1",
          "whitespace-nowrap [scrollbar-width:thin] scrollbar-thumb-border/60 scrollbar-track-transparent",
          "overscroll-x-contain snap-x snap-mandatory",
        )}
        style={{ WebkitOverflowScrolling: "touch" }}
        onKeyDown={handleArrowNavigation}
      >
        {options.map(({ key, label }) => {
          const active = activeCategory === key || (!activeCategory && key === "all");
          return (
            <button
              key={key}
              type="button"
              role="option"
              aria-selected={active}
              aria-pressed={active}
              onClick={() => onSelect(key)}
              className={cn(
                "inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-all duration-200 ease-out",
                "snap-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-white",
                active
                  ? "border-transparent bg-primary/90 text-primary-foreground"
                  : "border-border bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black",
              )}
            >
              <Icon name={resolveIconName(key)} className="h-4 w-4" aria-hidden />
              <span className="whitespace-nowrap">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}



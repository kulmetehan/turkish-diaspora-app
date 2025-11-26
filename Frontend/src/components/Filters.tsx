import { useMemo } from "react";

import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { surfaceTabsList, surfaceTabsTrigger } from "@/components/ui/tabStyles";
import { CategoryChips } from "@/components/search/CategoryChips";
import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import type { ViewMode } from "@/lib/routing/viewMode";
import { humanizeCategoryLabel } from "@/lib/categories";
import { cn } from "@/lib/ui/cn";

type CategoryOption = { key: string; label: string };

type Props = {
  search: string;
  category: string;
  onlyTurkish: boolean;
  loading?: boolean;
  categoryOptions?: CategoryOption[];
  suggestions?: string[];
  idPrefix?: string; // Optional prefix to make IDs unique (e.g., "desktop", "mobile")
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
  onChange: (patch: Partial<{
    search: string;
    category: string;
    onlyTurkish: boolean;
  }>) => void;
};

// Fallback categories if API fails (should rarely be used)
const FALLBACK_CATEGORIES: CategoryOption[] = [
  { key: "restaurant", label: "Restaurant" },
  { key: "bakery", label: "Bakkerij" },
  { key: "supermarket", label: "Supermarkt" },
  { key: "barber", label: "Barber" },
  { key: "mosque", label: "Moskee" },
  { key: "travel_agency", label: "Reisbureau" },
  { key: "butcher", label: "Slager" },
  { key: "fast_food", label: "Fastfood" },
  { key: "cafe", label: "Café" },
  { key: "car_dealer", label: "Autodealer" },
  { key: "insurance", label: "Verzekering" },
  { key: "tailor", label: "Kleermaker" },
];

export default function Filters({
  search,
  category,
  onlyTurkish,
  loading,
  categoryOptions,
  suggestions,
  idPrefix = "",
  viewMode,
  onViewModeChange,
  onChange,
}: Props) {
  const searchInputId = idPrefix ? `search-input-${idPrefix}` : "search-input";
  const categories = useMemo(() => {
    // Prefer categoryOptions from App.tsx (loaded from API)
    // Fall back to FALLBACK_CATEGORIES only if API hasn't loaded yet
    const base = (categoryOptions && categoryOptions.length)
      ? [...categoryOptions]
      : [...FALLBACK_CATEGORIES];

    // Ensure currently selected category is always included
    const withCurrent = (() => {
      if (!category || category === "all") return base;
      // If selected category already exists, return base
      if (base.some((c) => c.key === category)) return base;
      // Otherwise, append selected category so chip stays visible
      return [...base, { key: category, label: humanizeCategoryLabel(category) }];
    })();

    return withCurrent.sort((a, b) => a.key.localeCompare(b.key, "en"));
  }, [category, categoryOptions]);

  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-border bg-surface-raised p-4 text-foreground shadow-soft">
      {viewMode && onViewModeChange ? (
        <Tabs
          value={viewMode}
          onValueChange={(value) => {
            if (value === viewMode) return;
            if (value === "list" || value === "map") {
              onViewModeChange(value);
            }
          }}
        >
          <TabsList className={cn(surfaceTabsList, "grid w-full grid-cols-2 bg-card/80 text-xs")}>
            <TabsTrigger
              value="map"
              className={cn(surfaceTabsTrigger, "flex items-center justify-center gap-2 text-sm")}
            >
              <Icon name="Map" className="h-4 w-4" />
              Kaart
            </TabsTrigger>
            <TabsTrigger
              value="list"
              className={cn(surfaceTabsTrigger, "flex items-center justify-center gap-2 text-sm")}
            >
              <Icon name="List" className="h-4 w-4" />
              Lijst
            </TabsTrigger>
          </TabsList>
        </Tabs>
      ) : null}

      <FloatingSearchBar
        inputId={searchInputId}
        value={search}
        onValueChange={(next) => onChange({ search: next })}
        onClear={() => onChange({ search: "" })}
        suggestions={suggestions}
        placeholder="Zoek op naam of categorie…"
        ariaLabel="Zoek op naam of categorie"
      />

      {viewMode !== "map" ? (
        <CategoryChips
          categories={categories}
          activeCategory={category}
          onSelect={(key) => onChange({ category: key })}
        />
      ) : null}

      <div className="flex items-center gap-2 pt-2">
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200",
            onlyTurkish
              ? "border-transparent bg-primary text-primary-foreground shadow-soft"
              : "border-border bg-card text-foreground hover:bg-surface-muted",
          )}
          onClick={() => onChange({ onlyTurkish: !onlyTurkish })}
        >
          <Icon name={onlyTurkish ? "ShieldCheck" : "Users"} className="h-4 w-4" />
          Alleen Turks
        </button>

        {loading ? (
          <span className="text-xs text-muted-foreground">Laden…</span>
        ) : null}
      </div>
    </div>
  );
}

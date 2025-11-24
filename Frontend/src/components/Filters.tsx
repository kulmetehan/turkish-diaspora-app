import { useMemo, useRef, useState } from "react";

import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CategoryChips } from "@/components/search/CategoryChips";
import type { ViewMode } from "@/lib/routing/viewMode";
import { humanizeCategoryLabel } from "@/lib/categories";
import { Search, X } from "lucide-react";
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
  const [openSuggest, setOpenSuggest] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const suggestBoxRef = useRef<HTMLDivElement | null>(null);
  const showSuggestions = Boolean(openSuggest && suggestions && suggestions.length && search.trim().length);
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
    <div
      className={cn(
        "flex flex-col gap-4 rounded-3xl border border-white/10 bg-surface-raised/80 p-4 text-foreground shadow-soft",
        "supports-[backdrop-filter]:backdrop-blur-xl supports-[backdrop-filter]:bg-surface-raised/60",
      )}
    >
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
          <TabsList className="grid w-full grid-cols-2 rounded-2xl border border-white/10 bg-surface-muted/70 p-1 text-sm font-medium text-foreground/70 shadow-inner">
            <TabsTrigger value="map" className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm data-[state=active]:bg-surface-base data-[state=active]:text-foreground data-[state=active]:shadow-soft">
              <Icon name="Map" className="h-4 w-4" />
              Kaart
            </TabsTrigger>
            <TabsTrigger value="list" className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm data-[state=active]:bg-surface-base data-[state=active]:text-foreground data-[state=active]:shadow-soft">
              <Icon name="List" className="h-4 w-4" />
              Lijst
            </TabsTrigger>
          </TabsList>
        </Tabs>
      ) : null}

      <div className="relative" ref={suggestBoxRef}>
        <label htmlFor={searchInputId} className="sr-only">Zoek op naam of categorie</label>
        <div className="relative">
          <span className="absolute inset-y-0 left-3 flex items-center text-brand-white/70">
            <Search className="h-4 w-4" aria-hidden />
          </span>
          <Input
            id={searchInputId}
            name="search"
            placeholder="Zoek op naam of categorie…"
            className="h-12 rounded-2xl border border-white/10 bg-card pl-10 pr-12 text-base text-foreground placeholder:text-foreground/60 focus-visible:ring-brand-white/60"
            value={search}
            onChange={(e) => {
              onChange({ search: e.target.value });
              setOpenSuggest(true);
              setActiveIndex(0);
            }}
            onFocus={() => setOpenSuggest(true)}
            onBlur={() => {
              setTimeout(() => setOpenSuggest(false), 120);
            }}
            onKeyDown={(e) => {
              if (!suggestions || !suggestions.length) return;
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setOpenSuggest(true);
                setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setOpenSuggest(true);
                setActiveIndex((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                if (showSuggestions) {
                  e.preventDefault();
                  const s = suggestions[activeIndex];
                  if (s) onChange({ search: s });
                  setOpenSuggest(false);
                }
              } else if (e.key === "Escape") {
                if (search) onChange({ search: "" });
                setOpenSuggest(false);
              }
            }}
          />
          {search ? (
            <button
              type="button"
              className="absolute inset-y-0 right-3 flex items-center text-brand-white/70 transition-colors hover:text-brand-white"
              aria-label="Zoekveld wissen"
              onClick={() => {
                onChange({ search: "" });
                setOpenSuggest(false);
                setActiveIndex(0);
              }}
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>

          {showSuggestions ? (
          <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-white/10 bg-surface-raised text-sm shadow-soft">
            <div className="max-h-56 overflow-auto py-1">
              {suggestions!.map((s, idx) => (
                <button
                  type="button"
                  key={`${s}-${idx}`}
                  className={cn(
                    "w-full px-3 py-2 text-left text-foreground transition-colors",
                    idx === activeIndex
                      ? "bg-brand-accent-veil text-brand-white"
                      : "hover:bg-white/5",
                  )}
                  onMouseEnter={() => setActiveIndex(idx)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    onChange({ search: s });
                    setOpenSuggest(false);
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

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
              ? "border-transparent bg-[hsl(var(--brand-red-strong))] text-brand-white shadow-[0_10px_30px_rgba(0,0,0,0.35)]"
              : "border-border bg-surface-muted text-foreground hover:bg-surface-muted/80",
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

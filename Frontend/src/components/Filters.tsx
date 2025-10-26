import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";

type CategoryOption = { key: string; label: string };

type Props = {
  search: string;
  category: string;
  onlyTurkish: boolean;
  loading?: boolean;
  categoryOptions?: CategoryOption[];
  suggestions?: string[];
  onChange: (patch: Partial<{
    search: string;
    category: string;
    onlyTurkish: boolean;
  }>) => void;
};

// Officiële categorieën (TDA-107)
const KNOWN_CATEGORIES = [
  { key: "restaurant", label: "Restaurant" },
  { key: "bakery", label: "Bakkerij" },
  { key: "supermarket", label: "Supermarkt" },
  { key: "barber", label: "Barber" },
  { key: "mosque", label: "Moskee" },
  { key: "travel_agency", label: "Reisbureau" },
  { key: "butcher", label: "Slager" },
  { key: "fast_food", label: "Fastfood" },
] satisfies CategoryOption[];

function humanizeCategoryLabel(input: string | undefined | null): string {
  if (!input) return "—";

  let s = input as string;

  // Replace "_" and "/" with spaces (global)
  s = s.replace(/[_/]/g, " ");

  // Collapse multiple spaces and trim
  s = s.replace(/\s+/g, " ").trim();

  // Capitalize each word
  s = s
    .split(" ")
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");

  return s;
}

export default function Filters({
  search,
  category,
  onlyTurkish,
  loading,
  categoryOptions,
  suggestions,
  onChange,
}: Props) {
  const [openSuggest, setOpenSuggest] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const suggestBoxRef = useRef<HTMLDivElement | null>(null);
  const showSuggestions = Boolean(openSuggest && suggestions && suggestions.length && search.trim().length);
  const categories = useMemo(() => {
    const base = (categoryOptions && categoryOptions.length)
      ? categoryOptions
      : KNOWN_CATEGORIES;

    // Zorg dat de huidige category (als die buiten de lijst valt) toch zichtbaar is.
    if (!category || category === "all") return base;
    if (!base.some((c) => c.key === category)) {
      return [{ key: category, label: humanizeCategoryLabel(category) }, ...base];
    }
    return base;
  }, [category, categoryOptions]);

  return (
    <div className="rounded-xl border bg-card p-3 flex flex-col gap-3">
      <div className="relative" ref={suggestBoxRef}>
        <label htmlFor="search-input" className="sr-only">Zoek op naam of categorie</label>
        <div className="relative">
          <span className="absolute inset-y-0 left-2 flex items-center text-muted-foreground">
            <Search className="h-4 w-4" aria-hidden />
          </span>
          <Input
            id="search-input"
            name="search"
            placeholder="Zoek op naam of categorie…"
            className="pl-8 pr-8"
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
              className="absolute inset-y-0 right-2 flex items-center text-muted-foreground hover:text-foreground transition-colors"
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
          <div className="absolute mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-md overflow-hidden z-20">
            <div className="max-h-56 overflow-auto py-1 text-sm">
              {suggestions!.map((s, idx) => (
                <button
                  type="button"
                  key={`${s}-${idx}`}
                  className={`w-full text-left px-3 py-2 hover:bg-accent hover:text-accent-foreground ${idx === activeIndex ? "bg-accent/60" : ""}`}
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

      <div className="flex items-center gap-2 flex-wrap">
        <Button
          type="button"
          variant={category === "all" ? "secondary" : "outline"}
          size="sm"
          onClick={() => onChange({ category: "all" })}
        >
          Alle
        </Button>
        {categories.map((c) => {
          const active = category === c.key;
          const displayName = c.label || humanizeCategoryLabel(c.key);
          return (
            <Button
              key={c.key}
              type="button"
              variant={active ? "secondary" : "outline"}
              size="sm"
              onClick={() => onChange({ category: c.key })}
              className="rounded-full"
            >
              <Badge variant={active ? "default" : "outline"} className="pointer-events-none">
                {displayName}
              </Badge>
            </Button>
          );
        })}

        {loading ? (
          <span className="ml-auto text-xs text-muted-foreground">Laden…</span>
        ) : null}
      </div>
    </div>
  );
}

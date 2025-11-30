import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import {
  NL_CATEGORIES,
  TR_CATEGORIES,
  type NewsCategoryKey,
} from "@/lib/routing/newsCategories";
import type { NewsFeedKey } from "@/lib/routing/newsFeed";

const CATEGORY_LABELS: Record<NewsCategoryKey, string> = {
  general: "Algemeen",
  sport: "Sport",
  economie: "Economie",
  cultuur: "Cultuur",
  magazin: "Magazin",
};

export interface NewsCategoryFilterBarProps {
  feed: NewsFeedKey;
  selected: NewsCategoryKey[];
  onChange: (categories: NewsCategoryKey[]) => void;
  onClear?: () => void;
  className?: string;
}

export function NewsCategoryFilterBar({
  feed,
  selected,
  onChange,
  onClear,
  className,
}: NewsCategoryFilterBarProps) {
  const normalizedSelection = useMemo(() => {
    const seen = new Set<NewsCategoryKey>();
    const result: NewsCategoryKey[] = [];
    for (const category of selected) {
      if (!category || seen.has(category)) continue;
      seen.add(category);
      result.push(category);
    }
    return result;
  }, [selected]);

  // Show only NL categories when feed === "nl", only TR categories when feed === "tr"
  const availableCategories = useMemo(() => {
    if (feed === "nl") {
      return NL_CATEGORIES;
    } else if (feed === "tr") {
      return TR_CATEGORIES;
    }
    return []; // No categories for other feeds
  }, [feed]);

  const handleToggle = (category: NewsCategoryKey) => {
    const isActive = normalizedSelection.includes(category);
    const next = isActive
      ? normalizedSelection.filter((value) => value !== category)
      : [...normalizedSelection, category];
    onChange(next);
  };

  const handleClear = () => {
    if (!normalizedSelection.length) return;
    if (onClear) {
      onClear();
    } else {
      onChange([]);
    }
  };

  // Don't render if no categories available for this feed
  if (availableCategories.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 text-foreground shadow-soft",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Categorie filters
        </span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground"
          onClick={handleClear}
          disabled={!normalizedSelection.length}
        >
          Filters wissen
        </Button>
      </div>

      <div className="relative -mx-1">
        <div
          className="flex items-center gap-2 overflow-x-auto px-1 pb-1 whitespace-nowrap [scrollbar-width:thin] scrollbar-thumb-border/60 scrollbar-track-transparent snap-x snap-mandatory"
          style={{ WebkitOverflowScrolling: "touch" }}
        >
          {availableCategories.map((category) => {
            const active = normalizedSelection.includes(category);
            return (
              <button
                key={category}
                type="button"
                role="checkbox"
                aria-checked={active}
                onClick={() => handleToggle(category)}
                className={cn(
                  "inline-flex shrink-0 items-center rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200",
                  "snap-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
                  active
                    ? "border-transparent bg-accent text-accent-foreground shadow-soft"
                    : "border-border bg-card text-foreground hover:bg-surface-muted",
                )}
              >
                {CATEGORY_LABELS[category]}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}






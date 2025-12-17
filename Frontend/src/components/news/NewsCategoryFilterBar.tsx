// Frontend/src/components/news/NewsCategoryFilterBar.tsx
import { useMemo } from "react";

import {
  NL_CATEGORIES,
  TR_CATEGORIES,
  type NewsCategoryKey,
} from "@/lib/routing/newsCategories";
import type { NewsFeedKey } from "@/lib/routing/newsFeed";
import { cn } from "@/lib/ui/cn";

const CATEGORY_LABELS: Record<NewsCategoryKey, string> = {
  turks_nieuws: "Turks Nieuws",
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


  // Don't render if no categories available for this feed
  if (availableCategories.length === 0) {
    return null;
  }

  return (
    <div className={cn("relative", className)}>
      {/* Subtle separator line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-border/60 to-transparent" />
      <div
        className={cn(
          "flex gap-1.5 overflow-x-auto px-4 pt-3.5 pb-2",
          "bg-surface-base/50"
        )}
        style={{
          scrollbarWidth: "none", // Firefox
          msOverflowStyle: "none", // IE/Edge
        }}
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
                "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                active
                  ? "bg-primary/90 text-primary-foreground shadow-soft"
                  : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
              )}
            >
              {CATEGORY_LABELS[category]}
            </button>
          );
        })}
      </div>
    </div>
  );
}




















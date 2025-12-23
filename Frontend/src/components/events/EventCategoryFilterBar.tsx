// Frontend/src/components/events/EventCategoryFilterBar.tsx
import { useMemo } from "react";

import {
  EVENT_CATEGORIES,
  EVENT_CATEGORY_LABELS,
  type EventCategoryKey,
} from "@/lib/routing/eventCategories";
import { cn } from "@/lib/ui/cn";

export interface EventCategoryFilterBarProps {
  selected: EventCategoryKey[];
  onChange: (categories: EventCategoryKey[]) => void;
  onClear?: () => void;
  className?: string;
}

export function EventCategoryFilterBar({
  selected,
  onChange,
  onClear,
  className,
}: EventCategoryFilterBarProps) {
  const normalizedSelection = useMemo(() => {
    const seen = new Set<EventCategoryKey>();
    const result: EventCategoryKey[] = [];
    for (const category of selected) {
      if (!category || seen.has(category)) continue;
      seen.add(category);
      result.push(category);
    }
    return result;
  }, [selected]);

  const handleToggle = (category: EventCategoryKey) => {
    const isActive = normalizedSelection.includes(category);
    // Single select: always select only the clicked category, or deselect if already active
    onChange(isActive ? [] : [category]);
  };

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
        {EVENT_CATEGORIES.map((category) => {
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
              {EVENT_CATEGORY_LABELS[category]}
            </button>
          );
        })}
      </div>
    </div>
  );
}



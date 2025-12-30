// Frontend/src/components/favorites/FavoriteTabs.tsx
import { cn } from "@/lib/ui/cn";

export type FavoriteFilter = "mijn" | "anderen";

export interface FavoriteTabsProps {
  activeFilter: FavoriteFilter;
  onFilterChange: (filter: FavoriteFilter) => void;
  className?: string;
}

// Filter configuration: display label -> filter value
const FILTERS: Array<{ label: string; value: FavoriteFilter }> = [
  { label: "Mijn", value: "mijn" },
  { label: "Anderen", value: "anderen" },
];

export function FavoriteTabs({
  activeFilter,
  onFilterChange,
  className,
}: FavoriteTabsProps) {
  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto px-4 py-2",
        className
      )}
      style={{
        scrollbarWidth: "none", // Firefox
        msOverflowStyle: "none", // IE/Edge
      }}
    >
      {FILTERS.map((filter) => {
        const isActive = activeFilter === filter.value;
        return (
          <button
            key={filter.value}
            type="button"
            onClick={() => onFilterChange(filter.value)}
            className={cn(
              "flex-shrink-0 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              isActive
                ? "bg-primary text-primary-foreground shadow-soft"
                : "bg-gray-100 text-black hover:bg-gray-200"
            )}
            aria-pressed={isActive}
            aria-label={`Filter by ${filter.label}`}
          >
            {filter.label}
          </button>
        );
      })}
    </div>
  );
}


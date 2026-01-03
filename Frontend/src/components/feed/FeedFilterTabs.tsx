// Frontend/src/components/feed/FeedFilterTabs.tsx
import type { ActivityItem } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export type ActivityFilter = "all" | "one_cikanlar" | "timeline" | "music" | ActivityItem["activity_type"];

export interface FeedFilterTabsProps {
  activeFilter: ActivityFilter;
  onFilterChange: (filter: ActivityFilter) => void;
  className?: string;
}

// Filter configuration: translation key -> activity_type value
const FILTERS: Array<{ labelKey: string; value: ActivityFilter }> = [
  { labelKey: "feed.filters.all", value: "all" },
  { labelKey: "feed.filters.timeline", value: "timeline" },
  { labelKey: "feed.filters.oneCikanlar", value: "one_cikanlar" },
  { labelKey: "feed.filters.music", value: "music" },
  // { labelKey: "feed.filters.favorite", value: "favorite" }, // Temporarily hidden - will be re-enabled later
];

export function FeedFilterTabs({
  activeFilter,
  onFilterChange,
  className,
}: FeedFilterTabsProps) {
  const { t } = useTranslation();
  
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
        const label = t(filter.labelKey);
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
            aria-label={`Filter by ${label}`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}












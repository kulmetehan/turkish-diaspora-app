// Frontend/src/components/timeline/TimelineSubFilters.tsx
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export type TimelineSubFilter = "all" | "polls" | "check_ins" | "notes";

export interface TimelineSubFiltersProps {
  activeFilter: TimelineSubFilter;
  onFilterChange: (filter: TimelineSubFilter) => void;
  className?: string;
}

const SUB_FILTERS: Array<{ labelKey: string; value: TimelineSubFilter }> = [
  { labelKey: "timeline.filters.all", value: "all" },
  { labelKey: "timeline.filters.polls", value: "polls" },
  { labelKey: "timeline.filters.checkIns", value: "check_ins" },
  { labelKey: "timeline.filters.notes", value: "notes" },
];

export function TimelineSubFilters({
  activeFilter,
  onFilterChange,
  className,
}: TimelineSubFiltersProps) {
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
      {SUB_FILTERS.map((filter) => {
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


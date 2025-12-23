// Frontend/src/components/onecikanlar/PeriodTabs.tsx
import { cn } from "@/lib/ui/cn";

export type PeriodFilter = "today" | "week" | "month" | "city";

export interface PeriodTabsProps {
  activePeriod: PeriodFilter;
  onPeriodChange: (period: PeriodFilter) => void;
  className?: string;
}

// Period configuration: display label -> period value
const PERIODS: Array<{ label: string; value: PeriodFilter }> = [
  { label: "Bugün", value: "today" },
  { label: "Bu Hafta", value: "week" },
  { label: "Bu Ay", value: "month" },
  { label: "Şehir", value: "city" },
];

export function PeriodTabs({
  activePeriod,
  onPeriodChange,
  className,
}: PeriodTabsProps) {
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
      {PERIODS.map((period) => {
        const isActive = activePeriod === period.value;
        return (
          <button
            key={period.value}
            type="button"
            onClick={() => onPeriodChange(period.value)}
            className={cn(
              "flex-shrink-0 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              isActive
                ? "bg-primary text-primary-foreground shadow-soft"
                : "bg-gray-100 text-black hover:bg-gray-200"
            )}
            aria-pressed={isActive}
            aria-label={`Filter by ${period.label}`}
          >
            {period.label}
          </button>
        );
      })}
    </div>
  );
}



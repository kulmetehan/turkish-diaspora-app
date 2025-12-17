// Frontend/src/components/events/EventMonthFilterBar.tsx

import { cn } from "@/lib/ui/cn";

const MONTHS = [
  { key: 1, label: "Jan" },
  { key: 2, label: "Feb" },
  { key: 3, label: "Mrt" },
  { key: 4, label: "Apr" },
  { key: 5, label: "Mei" },
  { key: 6, label: "Jun" },
  { key: 7, label: "Jul" },
  { key: 8, label: "Aug" },
  { key: 9, label: "Sep" },
  { key: 10, label: "Okt" },
  { key: 11, label: "Nov" },
  { key: 12, label: "Dec" },
] as const;

export interface EventMonthFilterBarProps {
  selectedMonth: number | null;
  onMonthSelect: (month: number | null) => void;
  className?: string;
}

export function EventMonthFilterBar({
  selectedMonth,
  onMonthSelect,
  className,
}: EventMonthFilterBarProps) {
  const handleMonthClick = (month: number) => {
    if (selectedMonth === month) {
      // Deselect if clicking the same month
      onMonthSelect(null);
    } else {
      onMonthSelect(month);
    }
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
        {MONTHS.map((month) => {
          const active = selectedMonth === month.key;
          return (
            <button
              key={month.key}
              type="button"
              role="checkbox"
              aria-checked={active}
              onClick={() => handleMonthClick(month.key)}
              className={cn(
                "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                active
                  ? "bg-primary/90 text-primary-foreground shadow-soft"
                  : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
              )}
            >
              {month.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

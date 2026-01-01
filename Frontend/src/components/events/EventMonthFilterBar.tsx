// Frontend/src/components/events/EventMonthFilterBar.tsx

import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

const MONTH_KEYS = [
  { key: 1, translationKey: "events.months.jan" },
  { key: 2, translationKey: "events.months.feb" },
  { key: 3, translationKey: "events.months.mar" },
  { key: 4, translationKey: "events.months.apr" },
  { key: 5, translationKey: "events.months.may" },
  { key: 6, translationKey: "events.months.jun" },
  { key: 7, translationKey: "events.months.jul" },
  { key: 8, translationKey: "events.months.aug" },
  { key: 9, translationKey: "events.months.sep" },
  { key: 10, translationKey: "events.months.oct" },
  { key: 11, translationKey: "events.months.nov" },
  { key: 12, translationKey: "events.months.dec" },
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
  const { t } = useTranslation();
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
        {MONTH_KEYS.map((month) => {
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
              {t(month.translationKey)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

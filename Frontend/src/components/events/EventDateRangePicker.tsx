import { useCallback } from "react";

import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export interface EventDateRangePickerProps {
    dateFrom: string | null;
    dateTo: string | null;
    onDateFromChange: (date: string | null) => void;
    onDateToChange: (date: string | null) => void;
    onClear?: () => void;
}

export function EventDateRangePicker({
    dateFrom,
    dateTo,
    onDateFromChange,
    onDateToChange,
    onClear,
}: EventDateRangePickerProps) {
    const { t } = useTranslation();
    const handleFromChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const value = e.target.value;
            onDateFromChange(value || null);
        },
        [onDateFromChange]
    );

    const handleToChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const value = e.target.value;
            onDateToChange(value || null);
        },
        [onDateToChange]
    );

    const handleClear = useCallback(() => {
        onDateFromChange(null);
        onDateToChange(null);
        onClear?.();
    }, [onDateFromChange, onDateToChange, onClear]);

    const fromActive = dateFrom !== null;
    const toActive = dateTo !== null;
    const hasAnyDate = fromActive || toActive;

    return (
        <div className="px-4 py-2">
            <div className="flex items-center gap-1.5">
                {/* Van date picker */}
                <div className="flex items-center gap-1.5">
                    <label htmlFor="date-from" className="text-xs font-gilroy font-medium text-muted-foreground whitespace-nowrap">
                        {t("events.datePicker.from")}
                    </label>
                    <input
                        id="date-from"
                        type="date"
                        value={dateFrom || ""}
                        onChange={handleFromChange}
                        className={cn(
                            "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                            "cursor-pointer min-w-[120px]",
                            fromActive
                                ? "bg-primary/90 text-primary-foreground shadow-soft"
                                : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
                        )}
                    />
                </div>

                {/* Tot date picker */}
                <div className="flex items-center gap-1.5">
                    <label htmlFor="date-to" className="text-xs font-gilroy font-medium text-muted-foreground whitespace-nowrap">
                        {t("events.datePicker.to")}
                    </label>
                    <input
                        id="date-to"
                        type="date"
                        value={dateTo || ""}
                        onChange={handleToChange}
                        min={dateFrom || undefined}
                        className={cn(
                            "flex-shrink-0 rounded-sm px-3 py-1 text-xs font-gilroy font-medium transition-colors",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                            "cursor-pointer min-w-[120px]",
                            toActive
                                ? "bg-primary/90 text-primary-foreground shadow-soft"
                                : "bg-gray-100/80 text-black/70 hover:bg-gray-200/80 hover:text-black"
                        )}
                    />
                </div>

                {/* Clear button */}
                {hasAnyDate && (
                    <button
                        type="button"
                        onClick={handleClear}
                        className="text-xs text-muted-foreground hover:text-foreground underline ml-auto"
                    >
                        {t("events.datePicker.clear")}
                    </button>
                )}
            </div>
        </div>
    );
}












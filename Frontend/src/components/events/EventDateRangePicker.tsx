import { useCallback } from "react";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface EventDateRangePickerProps {
    dateFrom: string | null;
    dateTo: string | null;
    onDateFromChange: (date: string | null) => void;
    onDateToChange: (date: string | null) => void;
}

export function EventDateRangePicker({
    dateFrom,
    dateTo,
    onDateFromChange,
    onDateToChange,
}: EventDateRangePickerProps) {
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
    }, [onDateFromChange, onDateToChange]);

    return (
        <Card className="rounded-3xl border border-border bg-card p-4 shadow-soft">
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Datum filter</h3>
                    {(dateFrom || dateTo) && (
                        <button
                            type="button"
                            onClick={handleClear}
                            className="text-xs text-muted-foreground hover:text-foreground underline"
                        >
                            Wissen
                        </button>
                    )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="date-from" className="text-xs">
                            Van
                        </Label>
                        <Input
                            id="date-from"
                            type="date"
                            value={dateFrom || ""}
                            onChange={handleFromChange}
                            className="text-sm"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="date-to" className="text-xs">
                            Tot
                        </Label>
                        <Input
                            id="date-to"
                            type="date"
                            value={dateTo || ""}
                            onChange={handleToChange}
                            className="text-sm"
                            min={dateFrom || undefined}
                        />
                    </div>
                </div>
            </div>
        </Card>
    );
}











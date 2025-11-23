import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { EventSourceDTO } from "@/lib/apiAdmin";

export type EventSourceFormValues = {
    key: string;
    name: string;
    base_url: string;
    list_url?: string | null;
    selectors: Record<string, unknown>;
    interval_minutes: number;
    status: "active" | "disabled";
};

interface EventSourceFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initialSource?: EventSourceDTO | null;
    onSubmit: (values: EventSourceFormValues) => Promise<void> | void;
    loading?: boolean;
}

const DEFAULT_VALUES: EventSourceFormValues = {
    key: "",
    name: "",
    base_url: "",
    list_url: "",
    selectors: {},
    interval_minutes: 60,
    status: "active",
};

export default function EventSourceFormDialog({
    open,
    onOpenChange,
    initialSource,
    onSubmit,
    loading,
}: EventSourceFormDialogProps) {
    const [formValues, setFormValues] = useState<EventSourceFormValues>(DEFAULT_VALUES);
    const [selectorsText, setSelectorsText] = useState<string>("{}");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            if (initialSource) {
                setFormValues({
                    key: initialSource.key,
                    name: initialSource.name,
                    base_url: initialSource.base_url,
                    list_url: initialSource.list_url ?? "",
                    selectors: initialSource.selectors ?? {},
                    interval_minutes: initialSource.interval_minutes,
                    status: initialSource.status,
                });
                setSelectorsText(JSON.stringify(initialSource.selectors ?? {}, null, 2));
            } else {
                setFormValues(DEFAULT_VALUES);
                setSelectorsText("{}");
            }
            setError(null);
        }
    }, [open, initialSource]);

    const dialogTitle = initialSource ? "Edit Event Source" : "Add Event Source";
    const dialogDescription = initialSource
        ? "Update selectors, URLs, or scraping interval."
        : "Provide the website details and selectors to begin scraping events.";

    const handleChange = (field: keyof EventSourceFormValues, value: string) => {
        setFormValues((prev) => ({
            ...prev,
            [field]: field === "interval_minutes" ? Number(value) : value,
        }));
    };

    const handleSubmit = async () => {
        if (!formValues.key.trim() || !formValues.name.trim() || !formValues.base_url.trim()) {
            setError("Key, name, and base URL are required");
            return;
        }
        let parsedSelectors: Record<string, unknown> = {};
        try {
            const trimmed = selectorsText.trim();
            if (trimmed) {
                const parsed = JSON.parse(trimmed);
                if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
                    throw new Error("Selectors JSON must be an object");
                }
                parsedSelectors = parsed as Record<string, unknown>;
            }
        } catch (err: any) {
            setError(err?.message || "Selectors JSON is invalid");
            return;
        }
        setError(null);
        await onSubmit({
            ...formValues,
            list_url: formValues.list_url?.trim() ? formValues.list_url.trim() : null,
            selectors: parsedSelectors,
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>{dialogTitle}</DialogTitle>
                    <DialogDescription>{dialogDescription}</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="event-source-key">Key</Label>
                            <Input
                                id="event-source-key"
                                value={formValues.key}
                                onChange={(e) => handleChange("key", e.target.value)}
                                placeholder="rotterdam_culture"
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-source-name">Name</Label>
                            <Input
                                id="event-source-name"
                                value={formValues.name}
                                onChange={(e) => handleChange("name", e.target.value)}
                                placeholder="Rotterdam Cultuur Agenda"
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-source-base-url">Base URL</Label>
                            <Input
                                id="event-source-base-url"
                                value={formValues.base_url}
                                onChange={(e) => handleChange("base_url", e.target.value)}
                                placeholder="https://www.rotterdam.nl"
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-source-list-url">List URL (optional)</Label>
                            <Input
                                id="event-source-list-url"
                                value={formValues.list_url ?? ""}
                                onChange={(e) => handleChange("list_url", e.target.value)}
                                placeholder="https://www.rotterdam.nl/evenementen"
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-source-interval">Interval (minutes)</Label>
                            <Input
                                id="event-source-interval"
                                type="number"
                                min={5}
                                step={5}
                                value={formValues.interval_minutes}
                                onChange={(e) => handleChange("interval_minutes", e.target.value)}
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-source-status">Status</Label>
                            <select
                                id="event-source-status"
                                className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                                value={formValues.status}
                                onChange={(e) =>
                                    setFormValues((prev) => ({
                                        ...prev,
                                        status: e.target.value as "active" | "disabled",
                                    }))
                                }
                                disabled={loading}
                            >
                                <option value="active">Active</option>
                                <option value="disabled">Disabled</option>
                            </select>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="event-source-selectors">Selectors JSON</Label>
                        <Textarea
                            id="event-source-selectors"
                            value={selectorsText}
                            onChange={(e) => setSelectorsText(e.target.value)}
                            rows={8}
                            disabled={loading}
                            className="font-mono"
                        />
                        <p className="text-xs text-muted-foreground">
                            Provide a JSON object describing CSS selectors, e.g. {"{ \"list\": \".item\", \"title\": \".item-title\" }"}.
                        </p>
                    </div>
                    {error && <div className="text-sm text-destructive">{error}</div>}
                    <div className="flex justify-end gap-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button onClick={handleSubmit} disabled={loading}>
                            {loading ? "Saving..." : initialSource ? "Save changes" : "Create source"}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}



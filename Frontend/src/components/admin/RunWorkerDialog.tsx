import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { runWorker, type RunWorkerResponse } from "@/lib/apiAdmin";
import { fetchCategories, type CategoryOption } from "@/api/fetchLocations";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface RunWorkerDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    botId: string; // Backend bot value: "discovery", "verify", "classify", "monitor"
    onSuccess?: (response: RunWorkerResponse) => void;
}

// Hardcoded cities for now (can be loaded from API later)
const CITY_OPTIONS = [{ value: "rotterdam", label: "Rotterdam" }];

export default function RunWorkerDialog({
    open,
    onOpenChange,
    botId,
    onSuccess,
}: RunWorkerDialogProps) {
    const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState<boolean>(false);
    const [loading, setLoading] = useState(false);
    const [categories, setCategories] = useState<string>("");
    const [city, setCity] = useState<string>("rotterdam");
    const [limit, setLimit] = useState<string>("200");
    const [minConfidence, setMinConfidence] = useState<string>("0.8");
    const [dryRun, setDryRun] = useState<boolean>(false);
    const [errors, setErrors] = useState<Record<string, string>>({});

    // Load categories on mount
    useEffect(() => {
        if (open && botId === "discovery") {
            setCategoriesLoading(true);
            fetchCategories()
                .then(setCategoryOptions)
                .catch(() => {
                    // Silently fail, categories are optional
                    setCategoryOptions([]);
                })
                .finally(() => {
                    setCategoriesLoading(false);
                });
        }
    }, [open, botId]);

    // Reset form when dialog opens/closes or bot changes
    useEffect(() => {
        if (!open) {
            setCategories("");
            setCity("rotterdam");
            setLimit("200");
            setMinConfidence("0.8");
            setDryRun(false);
            setErrors({});
        }
    }, [open, botId]);

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (botId === "discovery") {
            if (!city || city.trim() === "") {
                newErrors.city = "City is required";
            }
            if (categories && categories.trim() !== "") {
                // Validate categories are comma-separated valid category keys
                const cats = categories.split(",").map((c) => c.trim()).filter(Boolean);
                const validKeys = categoryOptions.map((opt) => opt.key);
                const invalid = cats.filter((c) => !validKeys.includes(c));
                if (invalid.length > 0) {
                    newErrors.categories = `Invalid categories: ${invalid.join(", ")}`;
                }
            }
        }

        if (botId === "verify" || botId === "classify" || botId === "monitor") {
            const limitNum = parseInt(limit, 10);
            if (Number.isNaN(limitNum) || limitNum < 1 || limitNum > 1000) {
                newErrors.limit = "Limit must be between 1 and 1000";
            }
        }

        if (botId === "verify" || botId === "classify") {
            const confNum = parseFloat(minConfidence);
            if (Number.isNaN(confNum) || confNum < 0 || confNum > 1) {
                newErrors.minConfidence = "Min confidence must be between 0.0 and 1.0";
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async () => {
        if (!validateForm()) {
            return;
        }

        setLoading(true);
        try {
            const payload: { bot: string; city?: string; category?: string } = {
                bot: botId,
            };

            if (botId === "discovery") {
                payload.city = city;
                if (categories && categories.trim() !== "") {
                    // For now, only send first category (backend API only accepts single category)
                    const firstCategory = categories.split(",")[0].trim();
                    if (firstCategory) {
                        payload.category = firstCategory;
                    }
                }
            } else if (botId === "verify" || botId === "classify") {
                // Note: Backend API currently only accepts city/category, not limit/min_confidence
                // These would need to be passed via worker_runs.counters in a future update
                // For now, we'll just trigger the run with basic params
            }

            const response = await runWorker(payload);

            if (response.tracking_available === false) {
                toast.warning(
                    response.detail || "Worker run accepted, but progress tracking is not available yet."
                );
            } else {
                toast.success(
                    response.run_id
                        ? `Worker run created. Run ID: ${response.run_id.substring(0, 8)}...`
                        : "Worker run created."
                );
            }

            onSuccess?.(response);
            onOpenChange(false);
        } catch (error: any) {
            toast.error(error?.message || "Failed to trigger worker run.");
        } finally {
            setLoading(false);
        }
    };

    const renderDiscoveryForm = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="city">City *</Label>
                <Select value={city} onValueChange={setCity}>
                    <SelectTrigger id="city">
                        <SelectValue placeholder="Select city" />
                    </SelectTrigger>
                    <SelectContent>
                        {CITY_OPTIONS.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                {errors.city && <div className="text-sm text-red-600">{errors.city}</div>}
            </div>

            <div className="space-y-2">
                <Label htmlFor="categories">Categories (comma-separated, optional)</Label>
                <Input
                    id="categories"
                    value={categories}
                    onChange={(e) => setCategories(e.target.value)}
                    placeholder="e.g., bakery, restaurant"
                />
                {errors.categories && (
                    <div className="text-sm text-red-600">{errors.categories}</div>
                )}
                <div className="text-xs text-muted-foreground">
                    {categoriesLoading
                        ? "Loading categories..."
                        : categoryOptions.length > 0
                        ? `Available: ${categoryOptions.map((opt) => opt.label).join(", ")}`
                        : "No categories available"}
                </div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="dry-run-discovery" className="flex items-center gap-2 cursor-pointer">
                    <input
                        id="dry-run-discovery"
                        type="checkbox"
                        checked={dryRun}
                        onChange={(e) => setDryRun(e.target.checked)}
                        className="h-4 w-4 rounded border-input cursor-pointer"
                    />
                    <span>Dry run (no writes to database)</span>
                </Label>
            </div>
        </div>
    );

    const renderVerifyForm = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="limit-verify">Limit *</Label>
                <Input
                    id="limit-verify"
                    type="number"
                    min="1"
                    max="1000"
                    value={limit}
                    onChange={(e) => setLimit(e.target.value)}
                />
                {errors.limit && <div className="text-sm text-red-600">{errors.limit}</div>}
                <div className="text-xs text-muted-foreground">Number of records to process (1-1000)</div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="min-confidence-verify">Min Confidence *</Label>
                <Input
                    id="min-confidence-verify"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value)}
                />
                {errors.minConfidence && (
                    <div className="text-sm text-red-600">{errors.minConfidence}</div>
                )}
                <div className="text-xs text-muted-foreground">Minimum confidence score (0.0-1.0)</div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="dry-run-verify" className="flex items-center gap-2 cursor-pointer">
                    <input
                        id="dry-run-verify"
                        type="checkbox"
                        checked={dryRun}
                        onChange={(e) => setDryRun(e.target.checked)}
                        className="h-4 w-4 rounded border-input cursor-pointer"
                    />
                    <span>Dry run (no writes to database)</span>
                </Label>
            </div>
        </div>
    );

    const renderClassifyForm = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="limit-classify">Limit *</Label>
                <Input
                    id="limit-classify"
                    type="number"
                    min="1"
                    max="1000"
                    value={limit}
                    onChange={(e) => setLimit(e.target.value)}
                />
                {errors.limit && <div className="text-sm text-red-600">{errors.limit}</div>}
                <div className="text-xs text-muted-foreground">Number of records to process (1-1000)</div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="min-confidence-classify">Min Confidence *</Label>
                <Input
                    id="min-confidence-classify"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value)}
                />
                {errors.minConfidence && (
                    <div className="text-sm text-red-600">{errors.minConfidence}</div>
                )}
                <div className="text-xs text-muted-foreground">Minimum confidence score (0.0-1.0)</div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="dry-run-classify" className="flex items-center gap-2 cursor-pointer">
                    <input
                        id="dry-run-classify"
                        type="checkbox"
                        checked={dryRun}
                        onChange={(e) => setDryRun(e.target.checked)}
                        className="h-4 w-4 rounded border-input cursor-pointer"
                    />
                    <span>Dry run (no writes to database)</span>
                </Label>
            </div>
        </div>
    );

    const renderMonitorForm = () => (
        <div className="space-y-4">
            <div className="space-y-2">
                <Label htmlFor="limit-monitor">Limit *</Label>
                <Input
                    id="limit-monitor"
                    type="number"
                    min="1"
                    max="1000"
                    value={limit}
                    onChange={(e) => setLimit(e.target.value)}
                />
                {errors.limit && <div className="text-sm text-red-600">{errors.limit}</div>}
                <div className="text-xs text-muted-foreground">Number of records to process (1-1000)</div>
            </div>

            <div className="space-y-2">
                <Label htmlFor="dry-run-monitor" className="flex items-center gap-2 cursor-pointer">
                    <input
                        id="dry-run-monitor"
                        type="checkbox"
                        checked={dryRun}
                        onChange={(e) => setDryRun(e.target.checked)}
                        className="h-4 w-4 rounded border-input cursor-pointer"
                    />
                    <span>Dry run (no writes to database)</span>
                </Label>
            </div>
        </div>
    );

    const renderVerificationConsumerForm = () => (
        <div className="space-y-2 text-sm text-muted-foreground">
            <p>
                This worker consumes <span className="font-semibold">VERIFICATION</span> tasks created by MonitorBot,
                re-verifies locations, and updates their status and freshness.
            </p>
            <p>No additional parameters are required.</p>
        </div>
    );

    const renderForm = () => {
        switch (botId) {
            case "discovery":
                return renderDiscoveryForm();
            case "verify":
                return renderVerifyForm();
            case "classify":
                return renderClassifyForm();
            case "monitor":
                return renderMonitorForm();
            case "verification_consumer":
                return renderVerificationConsumerForm();
            default:
                return <div className="text-sm text-muted-foreground">Unknown bot type</div>;
        }
    };

    const botLabels: Record<string, string> = {
        discovery: "Discovery Bot",
        verify: "Verify Locations Bot",
        classify: "Classify Bot",
        monitor: "Monitor Bot",
        verification_consumer: "Verification Tasks Consumer",
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Run {botLabels[botId] || botId}</DialogTitle>
                    <DialogDescription>
                        Configure parameters for running the worker. Note: Some advanced parameters may
                        not be supported by the current API.
                    </DialogDescription>
                </DialogHeader>
                {renderForm()}
                <div className="flex justify-end gap-2 mt-6">
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={loading}>
                        {loading ? "Starting..." : "Run Worker"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}


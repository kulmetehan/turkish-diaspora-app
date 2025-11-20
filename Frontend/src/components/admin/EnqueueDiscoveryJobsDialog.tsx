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
// Using native checkbox input - no separate checkbox component available
import { enqueueDiscoveryJobs, getCities, type CityInfo } from "@/lib/apiAdmin";
import { getCityDistricts } from "@/lib/api";
import { fetchCategories, type CategoryOption } from "@/api/fetchLocations";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface EnqueueDiscoveryJobsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: (jobsCreated: number) => void;
}

const MAX_JOBS_HARD_LIMIT = 200;
const MAX_JOBS_SOFT_LIMIT = 50;

export default function EnqueueDiscoveryJobsDialog({
    open,
    onOpenChange,
    onSuccess,
}: EnqueueDiscoveryJobsDialogProps) {
    const [cities, setCities] = useState<CityInfo[]>([]);
    const [categories, setCategories] = useState<CategoryOption[]>([]);
    const [districts, setDistricts] = useState<string[]>([]);
    const [selectedCity, setSelectedCity] = useState<string>("");
    const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
    const [selectedDistricts, setSelectedDistricts] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(false);
    const [loadingCities, setLoadingCities] = useState(false);
    const [loadingDistricts, setLoadingDistricts] = useState(false);
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [showConfirm, setShowConfirm] = useState(false);
    const [estimatedJobs, setEstimatedJobs] = useState<number>(0);

    // Load cities and categories on mount
    useEffect(() => {
        if (open) {
            setLoadingCities(true);
            Promise.all([
                getCities(),
                fetchCategories().catch(() => []),
            ]).then(([citiesData, categoriesData]) => {
                setCities(citiesData);
                setCategories(categoriesData);
                if (citiesData.length > 0 && !selectedCity) {
                    setSelectedCity(citiesData[0].key);
                }
            }).catch((err) => {
                toast.error("Failed to load cities or categories");
                console.error(err);
            }).finally(() => {
                setLoadingCities(false);
            });
        }
    }, [open]);

    // Load districts when city changes
    useEffect(() => {
        if (open && selectedCity) {
            const city = cities.find((c) => c.key === selectedCity);
            if (city?.has_districts) {
                setLoadingDistricts(true);
                getCityDistricts(selectedCity)
                    .then((dists) => {
                        setDistricts(dists);
                    })
                    .catch((err) => {
                        toast.error("Failed to load districts");
                        console.error(err);
                        setDistricts([]);
                    })
                    .finally(() => {
                        setLoadingDistricts(false);
                    });
            } else {
                setDistricts([]);
                setSelectedDistricts(new Set());
            }
        }
    }, [open, selectedCity, cities]);

    // Calculate estimated jobs
    useEffect(() => {
        if (!selectedCity) {
            setEstimatedJobs(0);
            return;
        }

        const categoriesToUse = selectedCategories.size > 0
            ? Array.from(selectedCategories)
            : categories.map((c) => c.key);

        const districtsToUse = districts.length > 0 && selectedDistricts.size > 0
            ? Array.from(selectedDistricts)
            : districts.length > 0
            ? districts
            : null; // city-level

        const jobs = districtsToUse
            ? districtsToUse.length * categoriesToUse.length
            : categoriesToUse.length;

        setEstimatedJobs(jobs);
    }, [selectedCity, selectedCategories, selectedDistricts, categories, districts]);

    // Reset form when dialog closes
    useEffect(() => {
        if (!open) {
            setSelectedCity("");
            setSelectedCategories(new Set());
            setSelectedDistricts(new Set());
            setErrors({});
            setShowConfirm(false);
            setEstimatedJobs(0);
        }
    }, [open]);

    const handleCategoryToggle = (categoryKey: string) => {
        const newSet = new Set(selectedCategories);
        if (newSet.has(categoryKey)) {
            newSet.delete(categoryKey);
        } else {
            newSet.add(categoryKey);
        }
        setSelectedCategories(newSet);
    };

    const handleDistrictToggle = (districtKey: string) => {
        const newSet = new Set(selectedDistricts);
        if (newSet.has(districtKey)) {
            newSet.delete(districtKey);
        } else {
            newSet.add(districtKey);
        }
        setSelectedDistricts(newSet);
    };

    const handleSelectAllCategories = () => {
        if (selectedCategories.size === categories.length) {
            setSelectedCategories(new Set());
        } else {
            setSelectedCategories(new Set(categories.map((c) => c.key)));
        }
    };

    const handleSelectAllDistricts = () => {
        if (selectedDistricts.size === districts.length) {
            setSelectedDistricts(new Set());
        } else {
            setSelectedDistricts(new Set(districts));
        }
    };

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!selectedCity || selectedCity.trim() === "") {
            newErrors.city = "City is required";
        }

        if (estimatedJobs > MAX_JOBS_HARD_LIMIT) {
            newErrors.estimatedJobs = `Too many jobs (${estimatedJobs}). Maximum allowed: ${MAX_JOBS_HARD_LIMIT}`;
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async () => {
        if (!validateForm()) {
            return;
        }

        // Show confirmation if > soft limit
        if (estimatedJobs > MAX_JOBS_SOFT_LIMIT && !showConfirm) {
            setShowConfirm(true);
            return;
        }

        setLoading(true);
        try {
            const categoriesToUse = selectedCategories.size > 0
                ? Array.from(selectedCategories)
                : undefined; // undefined means "all" - backend will use all discoverable

            const districtsToUse = districts.length > 0
                ? (selectedDistricts.size > 0 ? Array.from(selectedDistricts) : undefined)
                : undefined; // undefined means city-level

            const response = await enqueueDiscoveryJobs({
                city_key: selectedCity,
                categories: categoriesToUse,
                districts: districtsToUse,
            });

            toast.success(
                `Successfully enqueued ${response.jobs_created} job(s) for ${response.preview.city}`
            );
            onSuccess?.(response.jobs_created);
            onOpenChange(false);
        } catch (error: any) {
            toast.error(error?.message || "Failed to enqueue jobs");
        } finally {
            setLoading(false);
        }
    };

    const currentCity = cities.find((c) => c.key === selectedCity);
    const showDistricts = currentCity?.has_districts && districts.length > 0;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Enqueue Discovery Jobs</DialogTitle>
                    <DialogDescription>
                        Create discovery jobs for a city, with optional filters for districts and categories.
                    </DialogDescription>
                </DialogHeader>

                {showConfirm ? (
                    <div className="space-y-4 py-4">
                        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                            <div className="font-semibold text-amber-900 mb-2">
                                Confirm: This will create {estimatedJobs} jobs
                            </div>
                            <div className="text-sm text-amber-800">
                                This action will create {estimatedJobs} discovery jobs, which may result in many OSM API calls.
                                Are you sure you want to continue?
                            </div>
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button
                                variant="outline"
                                onClick={() => setShowConfirm(false)}
                                disabled={loading}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleSubmit}
                                disabled={loading}
                                className="bg-amber-600 hover:bg-amber-700"
                            >
                                {loading ? "Enqueuing..." : "Yes, enqueue jobs"}
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4 py-4">
                        {/* City Selection */}
                        <div className="space-y-2">
                            <Label htmlFor="city-select">City *</Label>
                            <Select
                                value={selectedCity}
                                onValueChange={setSelectedCity}
                                disabled={loadingCities || loading}
                            >
                                <SelectTrigger id="city-select">
                                    <SelectValue placeholder={loadingCities ? "Loading cities..." : "Select city"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {cities.map((city) => (
                                        <SelectItem key={city.key} value={city.key}>
                                            {city.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {errors.city && (
                                <div className="text-sm text-red-600">{errors.city}</div>
                            )}
                        </div>

                        {/* Districts Selection */}
                        {showDistricts && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label>Districts (optional)</Label>
                                    {districts.length > 0 && (
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleSelectAllDistricts}
                                            className="h-auto py-1 text-xs"
                                        >
                                            {selectedDistricts.size === districts.length ? "Deselect all" : "Select all"}
                                        </Button>
                                    )}
                                </div>
                                <div className="border rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                                    {loadingDistricts ? (
                                        <div className="text-sm text-muted-foreground">Loading districts...</div>
                                    ) : districts.length === 0 ? (
                                        <div className="text-sm text-muted-foreground">No districts available</div>
                                    ) : (
                                        districts.map((district) => (
                                            <div key={district} className="flex items-center space-x-2">
                                                <input
                                                    id={`district-${district}`}
                                                    type="checkbox"
                                                    checked={selectedDistricts.has(district)}
                                                    onChange={() => handleDistrictToggle(district)}
                                                    disabled={loading}
                                                    className="h-4 w-4 rounded border-input cursor-pointer"
                                                />
                                                <Label
                                                    htmlFor={`district-${district}`}
                                                    className="text-sm font-normal cursor-pointer flex-1"
                                                >
                                                    {district}
                                                </Label>
                                            </div>
                                        ))
                                    )}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    {selectedDistricts.size === 0
                                        ? "No districts selected - will create city-level jobs"
                                        : `${selectedDistricts.size} district(s) selected`}
                                </div>
                            </div>
                        )}

                        {/* Categories Selection */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label>Categories (optional)</Label>
                                {categories.length > 0 && (
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={handleSelectAllCategories}
                                        className="h-auto py-1 text-xs"
                                    >
                                        {selectedCategories.size === categories.length ? "Deselect all" : "Select all"}
                                    </Button>
                                )}
                            </div>
                            <div className="border rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
                                {categories.length === 0 ? (
                                    <div className="text-sm text-muted-foreground">No categories available</div>
                                ) : (
                                    categories.map((category) => (
                                        <div key={category.key} className="flex items-center space-x-2">
                                            <input
                                                id={`category-${category.key}`}
                                                type="checkbox"
                                                checked={selectedCategories.has(category.key)}
                                                onChange={() => handleCategoryToggle(category.key)}
                                                disabled={loading}
                                                className="h-4 w-4 rounded border-input cursor-pointer"
                                            />
                                            <Label
                                                htmlFor={`category-${category.key}`}
                                                className="text-sm font-normal cursor-pointer flex-1"
                                            >
                                                {category.label || category.key}
                                            </Label>
                                        </div>
                                    ))
                                )}
                            </div>
                            <div className="text-xs text-muted-foreground">
                                {selectedCategories.size === 0
                                    ? "No categories selected - will use all discoverable categories"
                                    : `${selectedCategories.size} categor${selectedCategories.size === 1 ? "y" : "ies"} selected`}
                            </div>
                        </div>

                        {/* Preview */}
                        <div className="p-4 bg-muted rounded-lg space-y-2">
                            <div className="font-semibold">Preview</div>
                            <div className="text-sm">
                                This will create approximately <strong>{estimatedJobs}</strong> job(s):
                                <ul className="list-disc list-inside mt-1 ml-2 text-xs text-muted-foreground">
                                    <li>City: {currentCity?.name || selectedCity}</li>
                                    <li>
                                        Districts:{" "}
                                        {showDistricts
                                            ? selectedDistricts.size === 0
                                                ? "city-level"
                                                : `${selectedDistricts.size} selected`
                                            : "none (city-level)"}
                                    </li>
                                    <li>
                                        Categories:{" "}
                                        {selectedCategories.size === 0
                                            ? "all discoverable"
                                            : `${selectedCategories.size} selected`}
                                    </li>
                                </ul>
                            </div>
                            {estimatedJobs > MAX_JOBS_SOFT_LIMIT && (
                                <div className="text-xs text-amber-600 font-medium">
                                    ⚠️ Warning: This exceeds {MAX_JOBS_SOFT_LIMIT} jobs and will require confirmation.
                                </div>
                            )}
                            {errors.estimatedJobs && (
                                <div className="text-sm text-red-600">{errors.estimatedJobs}</div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex justify-end gap-2 mt-6">
                            <Button
                                variant="outline"
                                onClick={() => onOpenChange(false)}
                                disabled={loading}
                            >
                                Cancel
                            </Button>
                            <Button onClick={handleSubmit} disabled={loading || estimatedJobs === 0}>
                                {loading ? "Enqueuing..." : "Enqueue Jobs"}
                            </Button>
                        </div>
                    </div>
                )}
            </DialogContent>
        </Dialog>
    );
}


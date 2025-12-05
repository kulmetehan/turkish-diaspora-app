import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getCityDetail, type CityCreate, type CityUpdate, type CityReadiness, type CityDetailResponse } from "@/lib/apiAdmin";

export type CityFormValues = {
    city_name: string;
    country: string;
    center_lat: number;
    center_lng: number;
};

interface CityFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initialCity?: CityReadiness | null;
    onSubmit: (values: CityFormValues) => Promise<void> | void;
    loading?: boolean;
}

const DEFAULT_VALUES: CityFormValues = {
    city_name: "",
    country: "NL",
    center_lat: 52.0,
    center_lng: 4.5,
};

export default function CityFormDialog({
    open,
    onOpenChange,
    initialCity,
    onSubmit,
    loading,
}: CityFormDialogProps) {
    const [formValues, setFormValues] = useState<CityFormValues>(DEFAULT_VALUES);
    const [error, setError] = useState<string | null>(null);
    const [loadingCityDetail, setLoadingCityDetail] = useState(false);

    useEffect(() => {
        if (open) {
            if (initialCity) {
                setLoadingCityDetail(true);
                // Load full city details to get center coordinates and country
                getCityDetail(initialCity.city_key)
                    .then((cityDetail: CityDetailResponse) => {
                        setFormValues({
                            city_name: cityDetail.city_name,
                            country: cityDetail.country,
                            center_lat: cityDetail.center_lat,
                            center_lng: cityDetail.center_lng,
                        });
                        setError(null);
                    })
                    .catch((err: any) => {
                        setError(err?.message || "Failed to load city details");
                        // Fallback to available data
                        setFormValues({
                            city_name: initialCity.city_name,
                            country: "NL",
                            center_lat: 52.0,
                            center_lng: 4.5,
                        });
                    })
                    .finally(() => {
                        setLoadingCityDetail(false);
                    });
            } else {
                setFormValues(DEFAULT_VALUES);
                setError(null);
            }
        }
    }, [open, initialCity]);

    const dialogTitle = initialCity ? "Edit City" : "Add City";
    const dialogDescription = initialCity
        ? "Update city information."
        : "Create a new city with center coordinates.";

    const handleChange = (field: keyof CityFormValues, value: string | number) => {
        setFormValues((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const handleSubmit = async () => {
        if (!formValues.city_name.trim()) {
            setError("City name is required");
            return;
        }
        if (formValues.country.length !== 2) {
            setError("Country code must be 2 letters");
            return;
        }
        if (!(formValues.center_lat >= -90 && formValues.center_lat <= 90)) {
            setError("Latitude must be between -90 and 90");
            return;
        }
        if (!(formValues.center_lng >= -180 && formValues.center_lng <= 180)) {
            setError("Longitude must be between -180 and 180");
            return;
        }

        setError(null);
        try {
            await onSubmit(formValues);
        } catch (err: any) {
            setError(err?.message || "Failed to save city");
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>{dialogTitle}</DialogTitle>
                    <DialogDescription>{dialogDescription}</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="city_name">City Name *</Label>
                        <Input
                            id="city_name"
                            value={formValues.city_name}
                            onChange={(e) => handleChange("city_name", e.target.value)}
                            placeholder="e.g., Rotterdam, Den Haag"
                            disabled={loading}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="country">Country Code *</Label>
                        <Input
                            id="country"
                            value={formValues.country}
                            onChange={(e) => handleChange("country", e.target.value.toUpperCase())}
                            placeholder="NL"
                            maxLength={2}
                            disabled={loading}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="center_lat">Center Latitude *</Label>
                            <Input
                                id="center_lat"
                                type="number"
                                step="0.000001"
                                value={formValues.center_lat}
                                onChange={(e) => {
                                    const val = parseFloat(e.target.value);
                                    if (!isNaN(val)) {
                                        handleChange("center_lat", val);
                                    }
                                }}
                                placeholder="52.157284"
                                disabled={loading || loadingCityDetail}
                            />
                            <div className="text-xs text-muted-foreground">
                                Current: {formValues.center_lat.toFixed(6)}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="center_lng">Center Longitude *</Label>
                            <Input
                                id="center_lng"
                                type="number"
                                step="0.000001"
                                value={formValues.center_lng}
                                onChange={(e) => {
                                    const val = parseFloat(e.target.value);
                                    if (!isNaN(val)) {
                                        handleChange("center_lng", val);
                                    }
                                }}
                                placeholder="4.493417"
                                disabled={loading || loadingCityDetail}
                            />
                            <div className="text-xs text-muted-foreground">
                                Current: {formValues.center_lng.toFixed(6)}
                            </div>
                        </div>
                    </div>
                    {error && (
                        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                            {error}
                        </div>
                    )}
                </div>
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={loading}>
                        {loading ? "Saving..." : initialCity ? "Update" : "Create"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}


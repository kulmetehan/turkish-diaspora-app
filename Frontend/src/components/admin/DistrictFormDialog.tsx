import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DistrictCreate, DistrictUpdate } from "@/lib/apiAdmin";

// Calculate bounding box from center (same as backend)
const DEFAULT_DELTA = 0.015;

function calculateBbox(lat: number, lng: number) {
    return {
        lat_min: lat - DEFAULT_DELTA,
        lat_max: lat + DEFAULT_DELTA,
        lng_min: lng - DEFAULT_DELTA,
        lng_max: lng + DEFAULT_DELTA,
    };
}

export type DistrictFormValues = {
    name: string;
    center_lat: number;
    center_lng: number;
};

interface DistrictFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    cityKey: string;
    initialDistrict?: { key: string; name: string; center_lat?: number; center_lng?: number } | null;
    onSubmit: (values: DistrictFormValues) => Promise<void> | void;
    loading?: boolean;
}

const DEFAULT_VALUES: DistrictFormValues = {
    name: "",
    center_lat: 52.0,
    center_lng: 4.5,
};

export default function DistrictFormDialog({
    open,
    onOpenChange,
    cityKey,
    initialDistrict,
    onSubmit,
    loading,
}: DistrictFormDialogProps) {
    const [formValues, setFormValues] = useState<DistrictFormValues>(DEFAULT_VALUES);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            if (initialDistrict) {
                setFormValues({
                    name: initialDistrict.name || initialDistrict.key,
                    center_lat: initialDistrict.center_lat || 52.0,
                    center_lng: initialDistrict.center_lng || 4.5,
                });
            } else {
                setFormValues(DEFAULT_VALUES);
            }
            setError(null);
        }
    }, [open, initialDistrict]);

    const bbox = calculateBbox(formValues.center_lat, formValues.center_lng);
    const dialogTitle = initialDistrict ? "Edit District" : "Add District";
    const dialogDescription = initialDistrict
        ? "Update district information. Bounding box is automatically calculated from center coordinates."
        : "Create a new district. Bounding box will be automatically calculated from center coordinates (±0.015 degrees).";

    const handleChange = (field: keyof DistrictFormValues, value: string | number) => {
        setFormValues((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const handleSubmit = async () => {
        if (!formValues.name.trim()) {
            setError("District name is required");
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
            setError(err?.message || "Failed to save district");
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
                        <Label htmlFor="district_name">District Name *</Label>
                        <Input
                            id="district_name"
                            value={formValues.name}
                            onChange={(e) => handleChange("name", e.target.value)}
                            placeholder="e.g., Centrum, Zuid"
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
                                disabled={loading}
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
                                disabled={loading}
                            />
                            <div className="text-xs text-muted-foreground">
                                Current: {formValues.center_lng.toFixed(6)}
                            </div>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label>Calculated Bounding Box (preview)</Label>
                        <div className="bg-gray-50 p-3 rounded text-sm space-y-1">
                            <div>Lat: {bbox.lat_min.toFixed(6)} to {bbox.lat_max.toFixed(6)}</div>
                            <div>Lng: {bbox.lng_min.toFixed(6)} to {bbox.lng_max.toFixed(6)}</div>
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
                        {loading ? "Saving..." : initialDistrict ? "Update" : "Create"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}


import { useEffect, useState, type ChangeEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { CategoryOption } from "@/api/fetchLocations";
import { createAdminLocation, listAdminLocationCategories } from "@/lib/apiAdmin";

type Props = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
};

const EMPTY_FORM = {
    name: "",
    address: "",
    lat: "",
    lng: "",
    category: "",
    notes: "",
    evidence: "",
};

export default function AdminAddLocationDialog({ open, onOpenChange, onCreated }: Props) {
    const [form, setForm] = useState(EMPTY_FORM);
    const [categories, setCategories] = useState<CategoryOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadingCategories, setLoadingCategories] = useState(false);

    useEffect(() => {
        if (!open) return;
        setLoadingCategories(true);
        listAdminLocationCategories()
            .then((options) => {
                setCategories(options);
                if (options.length === 1) {
                    setForm((prev) => ({ ...prev, category: options[0].key }));
                }
            })
            .catch(() => {
                toast.error("Kon categorieën niet laden.");
            })
            .finally(() => setLoadingCategories(false));
    }, [open]);

    useEffect(() => {
        if (!open) {
            setForm(EMPTY_FORM);
        }
    }, [open]);

    const handleChange = (field: keyof typeof form) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

    const parseCoordinate = (value: string, label: string, range: [number, number]): number | null => {
        if (value.trim() === "") {
            toast.error(`${label} is verplicht.`);
            return null;
        }
        const parsed = Number(value);
        if (Number.isNaN(parsed)) {
            toast.error(`${label} moet een getal zijn.`);
            return null;
        }
        if (parsed < range[0] || parsed > range[1]) {
            toast.error(`${label} moet tussen ${range[0]} en ${range[1]} liggen.`);
            return null;
        }
        return parsed;
    };

    const handleSubmit = async () => {
        if (!form.name.trim() || !form.address.trim()) {
            toast.error("Naam en adres zijn verplicht.");
            return;
        }
        if (!form.category) {
            toast.error("Selecteer een categorie.");
            return;
        }
        const lat = parseCoordinate(form.lat, "Latitude", [-90, 90]);
        const lng = parseCoordinate(form.lng, "Longitude", [-180, 180]);
        if (lat == null || lng == null) return;

        const evidenceList = form.evidence
            .split(",")
            .map((entry) => entry.trim())
            .filter((entry) => entry.length > 0);

        setLoading(true);
        try {
            await createAdminLocation({
                name: form.name.trim(),
                address: form.address.trim(),
                lat,
                lng,
                category: form.category,
                notes: form.notes.trim() ? form.notes.trim() : undefined,
                evidence_urls: evidenceList.length > 0 ? evidenceList : undefined,
            });
            onCreated();
            onOpenChange(false);
            setForm(EMPTY_FORM);
        } catch (error: any) {
            toast.error(error?.message || "Kon locatie niet aanmaken.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(value) => onOpenChange(value)}>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Locatie toevoegen</DialogTitle>
                    <DialogDescription>Voeg een locatie handmatig toe aan de kaart. Vul alle velden zorgvuldig in.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="add-name">Naam</Label>
                            <Input id="add-name" value={form.name} onChange={handleChange("name")} placeholder="Naam van de locatie" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="add-category">Categorie</Label>
                            <Select
                                value={form.category}
                                onValueChange={(value) => setForm((prev) => ({ ...prev, category: value }))}
                                disabled={loadingCategories || categories.length === 0}
                            >
                                <SelectTrigger id="add-category">
                                    <SelectValue placeholder={loadingCategories ? "Laden..." : "Kies categorie"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {categories.map((option) => (
                                        <SelectItem key={option.key} value={option.key}>
                                            {option.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2 sm:col-span-2">
                            <Label htmlFor="add-address">Adres</Label>
                            <Input id="add-address" value={form.address} onChange={handleChange("address")} placeholder="Adres" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="add-lat">Latitude</Label>
                            <Input id="add-lat" type="number" value={form.lat} onChange={handleChange("lat")} placeholder="51.9230" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="add-lng">Longitude</Label>
                            <Input id="add-lng" type="number" value={form.lng} onChange={handleChange("lng")} placeholder="4.4850" />
                        </div>
                        <div className="space-y-2 sm:col-span-2">
                            <Label htmlFor="add-notes">Notities</Label>
                            <textarea
                                id="add-notes"
                                className="w-full rounded-md border bg-background p-2 text-sm"
                                rows={3}
                                value={form.notes}
                                onChange={handleChange("notes")}
                                placeholder="Optioneel: context voor deze locatie"
                            />
                        </div>
                        <div className="space-y-2 sm:col-span-2">
                            <Label htmlFor="add-evidence">Evidence URL's</Label>
                            <Input
                                id="add-evidence"
                                value={form.evidence}
                                onChange={handleChange("evidence")}
                                placeholder="Komma-gescheiden lijst met URL's"
                            />
                        </div>
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                            Annuleer
                        </Button>
                        <Button onClick={handleSubmit} disabled={loading || loadingCategories}>
                            {loading ? "Bezig..." : "Opslaan"}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}


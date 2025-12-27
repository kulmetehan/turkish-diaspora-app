import { useEffect, useState, type ChangeEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import type { CategoryOption } from "@/api/fetchLocations";
import { fetchCategories } from "@/api/fetchLocations";
import { geocodeAddress, submitLocation } from "@/lib/api";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLocationSelected?: (lat: number, lng: number) => void;
  selectedLat?: number | null;
  selectedLng?: number | null;
  onLocationModeChange?: (mode: "map" | "address") => void;
};

const EMPTY_FORM = {
  name: "",
  address: "",
  category: "",
  customCategory: "",
  is_owner: false,
};

const CUSTOM_CATEGORY_VALUE = "__custom__";

export default function AddLocationDialog({
  open,
  onOpenChange,
  onLocationSelected,
  selectedLat,
  selectedLng,
  onLocationModeChange,
}: Props) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [locationMode, setLocationMode] = useState<"map" | "address">("map");
  const [geocodeAddressInput, setGeocodeAddressInput] = useState("");

  useEffect(() => {
    if (!open) {
      setForm(EMPTY_FORM);
      setGeocodeAddressInput("");
      setLocationMode("map");
      setGeocoding(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setLoadingCategories(true);
    fetchCategories()
      .then((options) => {
        setCategories(options);
      })
      .catch(() => {
        toast.error("Kon categorieën niet laden.");
      })
      .finally(() => setLoadingCategories(false));
  }, [open]);

  const handleChange = (field: keyof typeof form) => (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const handleCategoryChange = (value: string) => {
    if (value === CUSTOM_CATEGORY_VALUE) {
      setForm((prev) => ({ ...prev, category: CUSTOM_CATEGORY_VALUE, customCategory: "" }));
    } else {
      setForm((prev) => ({ ...prev, category: value, customCategory: "" }));
    }
  };

  const handleGeocode = async () => {
    if (!geocodeAddressInput.trim()) {
      toast.error("Voer een adres in.");
      return;
    }

    setGeocoding(true);
    try {
      const result = await geocodeAddress(geocodeAddressInput.trim());
      onLocationSelected?.(result.lat, result.lng);
      toast.success("Adres gevonden!");
    } catch (error: any) {
      toast.error(error?.message || "Kon adres niet vinden. Probeer een specifieker adres.");
    } finally {
      setGeocoding(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      toast.error("Naam is verplicht.");
      return;
    }

    const finalCategory = form.category === CUSTOM_CATEGORY_VALUE ? form.customCategory.trim() : form.category;
    if (!finalCategory) {
      toast.error("Selecteer een categorie of voer een custom categorie in.");
      return;
    }

    const lat = selectedLat;
    const lng = selectedLng;

    if (lat == null || lng == null || !isFinite(lat) || !isFinite(lng)) {
      toast.error("Selecteer een locatie op de kaart of geocodeer een adres.");
      return;
    }

    setLoading(true);
    try {
      await submitLocation({
        name: form.name.trim(),
        address: form.address.trim() || undefined,
        lat,
        lng,
        category: finalCategory,
        is_owner: form.is_owner,
      });
      toast.success("Locatie ingediend! U ontvangt een e-mail over het resultaat.");
      onOpenChange(false);
      setForm(EMPTY_FORM);
      setGeocodeAddressInput("");
      setLocationMode("map");
    } catch (error: any) {
      toast.error(error?.message || "Kon locatie niet indienen.");
    } finally {
      setLoading(false);
    }
  };

  const hasLocation = selectedLat != null && selectedLng != null && isFinite(selectedLat) && isFinite(selectedLng);
  const isCustomCategory = form.category === CUSTOM_CATEGORY_VALUE;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Locatie toevoegen</DialogTitle>
          <DialogDescription>
            Voeg een nieuwe locatie toe aan de kaart. Na indiening wordt deze beoordeeld door een admin.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {/* Naam */}
          <div className="space-y-2">
            <Label htmlFor="add-location-name">Naam *</Label>
            <Input
              id="add-location-name"
              value={form.name}
              onChange={handleChange("name")}
              placeholder="Naam van de locatie"
            />
          </div>

          {/* Locatie selectie */}
          <div className="space-y-2">
            <Label>Locatie *</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={locationMode === "map" ? "default" : "outline"}
                onClick={() => {
                  setLocationMode("map");
                  onLocationModeChange?.("map");
                }}
                className="flex-1"
              >
                Klik op kaart
              </Button>
              <Button
                type="button"
                variant={locationMode === "address" ? "default" : "outline"}
                onClick={() => {
                  setLocationMode("address");
                  onLocationModeChange?.("address");
                }}
                className="flex-1"
              >
                Voer adres in
              </Button>
            </div>

            {locationMode === "map" ? (
              <div className="text-sm text-muted-foreground">
                {hasLocation ? (
                  <span className="text-green-600">✓ Locatie geselecteerd: {selectedLat?.toFixed(6)}, {selectedLng?.toFixed(6)}</span>
                ) : (
                  <span>Klik op de kaart om een locatie te selecteren</span>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input
                    value={geocodeAddressInput}
                    onChange={(e) => setGeocodeAddressInput(e.target.value)}
                    placeholder="Bijv. Rotterdam, Nederland"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleGeocode();
                      }
                    }}
                  />
                  <Button type="button" onClick={handleGeocode} disabled={geocoding}>
                    {geocoding ? "Zoeken..." : "Zoek"}
                  </Button>
                </div>
                {hasLocation && (
                  <div className="text-sm text-green-600">
                    ✓ Adres gevonden: {selectedLat?.toFixed(6)}, {selectedLng?.toFixed(6)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Adres (optioneel) */}
          <div className="space-y-2">
            <Label htmlFor="add-location-address">Adres (optioneel)</Label>
            <Input
              id="add-location-address"
              value={form.address}
              onChange={handleChange("address")}
              placeholder="Volledig adres voor context"
            />
          </div>

          {/* Categorie */}
          <div className="space-y-2">
            <Label htmlFor="add-location-category">Categorie *</Label>
            <Select
              value={form.category}
              onValueChange={handleCategoryChange}
              disabled={loadingCategories || categories.length === 0}
            >
              <SelectTrigger id="add-location-category">
                <SelectValue placeholder={loadingCategories ? "Laden..." : "Kies categorie"} />
              </SelectTrigger>
              <SelectContent>
                {categories.map((option) => (
                  <SelectItem key={option.key} value={option.key}>
                    {option.label}
                  </SelectItem>
                ))}
                <SelectItem value={CUSTOM_CATEGORY_VALUE}>Anders namelijk:</SelectItem>
              </SelectContent>
            </Select>
            {isCustomCategory && (
              <Input
                value={form.customCategory}
                onChange={handleChange("customCategory")}
                placeholder="Voer uw categorie in"
                className="mt-2"
              />
            )}
          </div>

          {/* Is Owner Checkbox */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="add-location-is-owner"
              checked={form.is_owner}
              onCheckedChange={(checked) => setForm((prev) => ({ ...prev, is_owner: checked === true }))}
            />
            <Label htmlFor="add-location-is-owner" className="cursor-pointer">
              Ik ben de eigenaar van deze locatie
            </Label>
          </div>

          {/* Submit buttons */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Annuleer
            </Button>
            <Button onClick={handleSubmit} disabled={loading || loadingCategories || !hasLocation}>
              {loading ? "Bezig..." : "Indienen"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


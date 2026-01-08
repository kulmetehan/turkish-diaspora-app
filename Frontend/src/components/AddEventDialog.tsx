import { useEffect, useState, type ChangeEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { EVENT_CATEGORIES, type EventCategoryKey } from "@/lib/routing/eventCategories";
import { geocodeEventAddress, submitEvent } from "@/lib/api";
import type { EventSubmissionCreate } from "@/lib/apiEvents";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLocationSelected?: (lat: number, lng: number) => void;
  selectedLat?: number | null;
  selectedLng?: number | null;
  onLocationModeChange?: (mode: "map" | "address") => void;
};

const EMPTY_FORM: Omit<EventSubmissionCreate, "start_time_utc"> & {
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
} = {
  title: "",
  description: "",
  start_date: "",
  start_time: "",
  end_date: "",
  end_time: "",
  location_text: "",
  lat: undefined,
  lng: undefined,
  url: "",
  category_key: undefined,
};

export default function AddEventDialog({
  open,
  onOpenChange,
  onLocationSelected,
  selectedLat,
  selectedLng,
  onLocationModeChange,
}: Props) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
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

  const handleChange = (field: keyof typeof form) => (
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const handleGeocode = async () => {
    if (!geocodeAddressInput.trim()) {
      toast.error("Voer een adres in.");
      return;
    }

    setGeocoding(true);
    try {
      const result = await geocodeEventAddress(geocodeAddressInput.trim());
      onLocationSelected?.(result.lat, result.lng);
      setForm((prev) => ({ ...prev, lat: result.lat, lng: result.lng }));
      toast.success("Adres gevonden!");
    } catch (error: any) {
      toast.error(error?.message || "Kon adres niet vinden. Probeer een specifieker adres.");
    } finally {
      setGeocoding(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.title.trim()) {
      toast.error("Titel is verplicht.");
      return;
    }

    if (!form.start_date || !form.start_time) {
      toast.error("Start datum en tijd zijn verplicht.");
      return;
    }

    // Combine date and time into ISO string
    const startDateTime = new Date(`${form.start_date}T${form.start_time}`);
    if (isNaN(startDateTime.getTime())) {
      toast.error("Ongeldige start datum/tijd.");
      return;
    }

    // Validate start time is in the future
    if (startDateTime <= new Date()) {
      toast.error("Start tijd moet in de toekomst zijn.");
      return;
    }

    let endDateTime: Date | undefined;
    if (form.end_date && form.end_time) {
      endDateTime = new Date(`${form.end_date}T${form.end_time}`);
      if (isNaN(endDateTime.getTime())) {
        toast.error("Ongeldige eind datum/tijd.");
        return;
      }
      if (endDateTime <= startDateTime) {
        toast.error("Eind tijd moet na start tijd zijn.");
        return;
      }
    }

    // Validate URL if provided
    if (form.url && form.url.trim()) {
      const url = form.url.trim();
      if (!url.startsWith("http://") && !url.startsWith("https://")) {
        toast.error("URL moet beginnen met http:// of https://");
        return;
      }
    }

    const submission: EventSubmissionCreate = {
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      start_time_utc: startDateTime.toISOString(),
      end_time_utc: endDateTime?.toISOString(),
      location_text: form.location_text.trim() || undefined,
      lat: selectedLat ?? form.lat,
      lng: selectedLng ?? form.lng,
      url: form.url.trim() || undefined,
      category_key: form.category_key || undefined,
    };

    setLoading(true);
    try {
      await submitEvent(submission);
      toast.success("Event ingediend! U ontvangt een e-mail over het resultaat.");
      onOpenChange(false);
      setForm(EMPTY_FORM);
      setGeocodeAddressInput("");
      setLocationMode("map");
    } catch (error: any) {
      toast.error(error?.message || "Kon event niet indienen.");
    } finally {
      setLoading(false);
    }
  };

  const hasLocation = (selectedLat != null && selectedLng != null && isFinite(selectedLat) && isFinite(selectedLng)) ||
    (form.lat != null && form.lng != null && isFinite(form.lat) && isFinite(form.lng));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Event toevoegen</DialogTitle>
          <DialogDescription>
            Voeg een nieuw event toe. Na indiening wordt deze beoordeeld door een admin.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {/* Titel */}
          <div className="space-y-2">
            <Label htmlFor="add-event-title">Titel *</Label>
            <Input
              id="add-event-title"
              value={form.title}
              onChange={handleChange("title")}
              placeholder="Titel van het event"
            />
          </div>

          {/* Beschrijving */}
          <div className="space-y-2">
            <Label htmlFor="add-event-description">Beschrijving (optioneel)</Label>
            <Textarea
              id="add-event-description"
              value={form.description}
              onChange={handleChange("description")}
              placeholder="Beschrijving van het event"
              rows={4}
            />
          </div>

          {/* Start datum/tijd */}
          <div className="space-y-2">
            <Label>Start datum en tijd *</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="add-event-start-date" className="text-xs text-muted-foreground">Datum</Label>
                <Input
                  id="add-event-start-date"
                  type="date"
                  value={form.start_date}
                  onChange={handleChange("start_date")}
                  min={new Date().toISOString().split("T")[0]}
                />
              </div>
              <div>
                <Label htmlFor="add-event-start-time" className="text-xs text-muted-foreground">Tijd</Label>
                <Input
                  id="add-event-start-time"
                  type="time"
                  value={form.start_time}
                  onChange={handleChange("start_time")}
                />
              </div>
            </div>
          </div>

          {/* Eind datum/tijd */}
          <div className="space-y-2">
            <Label>Eind datum en tijd (optioneel)</Label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label htmlFor="add-event-end-date" className="text-xs text-muted-foreground">Datum</Label>
                <Input
                  id="add-event-end-date"
                  type="date"
                  value={form.end_date}
                  onChange={handleChange("end_date")}
                  min={form.start_date || new Date().toISOString().split("T")[0]}
                />
              </div>
              <div>
                <Label htmlFor="add-event-end-time" className="text-xs text-muted-foreground">Tijd</Label>
                <Input
                  id="add-event-end-time"
                  type="time"
                  value={form.end_time}
                  onChange={handleChange("end_time")}
                />
              </div>
            </div>
          </div>

          {/* Locatie selectie */}
          <div className="space-y-2">
            <Label>Locatie (optioneel)</Label>
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
                  <span className="text-green-600">
                    ✓ Locatie geselecteerd: {selectedLat?.toFixed(6) ?? form.lat?.toFixed(6)}, {selectedLng?.toFixed(6) ?? form.lng?.toFixed(6)}
                  </span>
                ) : (
                  <span>Klik op de kaart om een locatie te selecteren (optioneel)</span>
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
                    ✓ Adres gevonden: {selectedLat?.toFixed(6) ?? form.lat?.toFixed(6)}, {selectedLng?.toFixed(6) ?? form.lng?.toFixed(6)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Locatie tekst */}
          <div className="space-y-2">
            <Label htmlFor="add-event-location-text">Locatie tekst (optioneel)</Label>
            <Input
              id="add-event-location-text"
              value={form.location_text}
              onChange={handleChange("location_text")}
              placeholder="Bijv. Concertzaal, Rotterdam"
            />
          </div>

          {/* URL */}
          <div className="space-y-2">
            <Label htmlFor="add-event-url">Event URL (optioneel)</Label>
            <Input
              id="add-event-url"
              type="url"
              value={form.url}
              onChange={handleChange("url")}
              placeholder="https://..."
            />
          </div>

          {/* Categorie */}
          <div className="space-y-2">
            <Label htmlFor="add-event-category">Categorie (optioneel)</Label>
            <Select
              value={form.category_key || ""}
              onValueChange={(value) => setForm((prev) => ({ ...prev, category_key: value || undefined }))}
            >
              <SelectTrigger id="add-event-category">
                <SelectValue placeholder="Kies categorie" />
              </SelectTrigger>
              <SelectContent>
                {EVENT_CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Submit buttons */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Annuleer
            </Button>
            <Button onClick={handleSubmit} disabled={loading || !form.title.trim() || !form.start_date || !form.start_time}>
              {loading ? "Bezig..." : "Indienen"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


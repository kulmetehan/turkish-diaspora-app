import { useState, useEffect, ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createOutreachContact, type AdminContactCreate } from "@/lib/apiAdmin";
import { toast } from "sonner";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
  locationId?: number; // Optional pre-filled location ID
  locationName?: string; // Optional location name for display
};

const EMPTY_FORM: AdminContactCreate = {
  location_id: 0,
  email: "",
  confidence_score: 100,
};

export default function AddContactDialog({ open, onOpenChange, onCreated, locationId, locationName }: Props) {
  const [form, setForm] = useState<AdminContactCreate>(EMPTY_FORM);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      // Pre-fill location_id if provided
      setForm({
        ...EMPTY_FORM,
        location_id: locationId || 0,
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [open, locationId]);

  const handleChange = (field: keyof typeof form) => (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.value;
    if (field === "location_id") {
      setForm((prev) => ({ ...prev, [field]: parseInt(value, 10) || 0 }));
    } else if (field === "confidence_score") {
      setForm((prev) => ({ ...prev, [field]: parseInt(value, 10) || 100 }));
    } else {
      setForm((prev) => ({ ...prev, [field]: value }));
    }
  };

  const handleSubmit = async () => {
    // Validation
    if (!form.location_id || form.location_id <= 0) {
      toast.error("Location ID is required and must be greater than 0");
      return;
    }

    if (!form.email || !form.email.trim()) {
      toast.error("Email is required");
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(form.email.trim())) {
      toast.error("Invalid email format");
      return;
    }

    if (form.confidence_score !== undefined) {
      if (form.confidence_score < 0 || form.confidence_score > 100) {
        toast.error("Confidence score must be between 0 and 100");
        return;
      }
    }

    setLoading(true);
    try {
      await createOutreachContact({
        location_id: form.location_id,
        email: form.email.trim().toLowerCase(),
        confidence_score: form.confidence_score || 100,
      });
      toast.success("Contact created successfully");
      onCreated();
      onOpenChange(false);
      setForm(EMPTY_FORM);
    } catch (error: any) {
      toast.error(`Failed to create contact: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Outreach Contact</DialogTitle>
          <DialogDescription>
            {locationName
              ? `Add contact email for "${locationName}". This contact will be marked with source "manual".`
              : "Manually add a contact email for a location. This contact will be marked with source \"manual\"."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="contact-location-id">Location ID *</Label>
            <Input
              id="contact-location-id"
              type="number"
              value={form.location_id || ""}
              onChange={handleChange("location_id")}
              placeholder="123"
              min="1"
              disabled={!!locationId} // Disable if pre-filled
            />
            {locationName && (
              <p className="text-xs text-muted-foreground">
                Location: {locationName}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact-email">Email *</Label>
            <Input
              id="contact-email"
              type="email"
              value={form.email}
              onChange={handleChange("email")}
              placeholder="contact@example.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact-confidence">Confidence Score (0-100)</Label>
            <Input
              id="contact-confidence"
              type="number"
              value={form.confidence_score || 100}
              onChange={handleChange("confidence_score")}
              placeholder="100"
              min="0"
              max="100"
            />
            <p className="text-xs text-muted-foreground">
              Default: 100 (admin-created contacts have high confidence)
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Creating..." : "Create Contact"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


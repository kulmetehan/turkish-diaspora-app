// Frontend/src/components/promotions/PromoteLocationForm.tsx
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  createLocationPromotion,
  getClaimedLocations,
  type ClaimedLocation,
  type CreateLocationPromotionRequest,
} from "@/lib/api/promotions";
import { loadStripe } from "@stripe/stripe-js";

interface Props {
  onSuccess: () => void;
  onCancel: () => void;
}

const DURATION_OPTIONS = [
  { value: 7, label: "7 days", price: "€50" },
  { value: 14, label: "14 days", price: "€90" },
  { value: 30, label: "30 days", price: "€150" },
];

export default function PromoteLocationForm({ onSuccess, onCancel }: Props) {
  const [locations, setLocations] = useState<ClaimedLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<CreateLocationPromotionRequest>({
    location_id: 0,
    promotion_type: "trending",
    duration_days: 7,
  });

  useEffect(() => {
    loadLocations();
  }, []);

  const loadLocations = async () => {
    try {
      const data = await getClaimedLocations();
      setLocations(data);
      if (data.length > 0) {
        setFormData((prev) => ({ ...prev, location_id: data[0].id }));
      }
    } catch (err) {
      toast.error("Failed to load locations", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.location_id) {
      toast.error("Please select a location");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createLocationPromotion(formData);
      
      // Redirect to Stripe Checkout
      if (result.client_secret) {
        const stripe = await loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || "");
        if (stripe) {
          await stripe.confirmCardPayment(result.client_secret);
          toast.success("Payment processed successfully");
          onSuccess();
        } else {
          toast.error("Stripe not configured");
        }
      } else {
        toast.success("Promotion created");
        onSuccess();
      }
    } catch (err) {
      toast.error("Failed to create promotion", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <Card><CardContent className="py-8">Loading locations...</CardContent></Card>;
  }

  if (locations.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No claimed locations available. Please claim a location first.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Promote Location</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="location">Location</Label>
            <Select
              value={formData.location_id.toString()}
              onValueChange={(value) =>
                setFormData((prev) => ({ ...prev, location_id: parseInt(value) }))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select location" />
              </SelectTrigger>
              <SelectContent>
                {locations.map((loc) => (
                  <SelectItem key={loc.id} value={loc.id.toString()}>
                    {loc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="promotion_type">Promotion Type</Label>
            <Select
              value={formData.promotion_type}
              onValueChange={(value: "trending" | "feed" | "both") =>
                setFormData((prev) => ({ ...prev, promotion_type: value }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="trending">Trending Only</SelectItem>
                <SelectItem value="feed">Feed Only</SelectItem>
                <SelectItem value="both">Both (Trending + Feed)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="duration">Duration</Label>
            <Select
              value={formData.duration_days.toString()}
              onValueChange={(value) =>
                setFormData((prev) => ({ ...prev, duration_days: parseInt(value) as 7 | 14 | 30 }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DURATION_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value.toString()}>
                    {opt.label} - {opt.price}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Processing..." : "Create Promotion"}
            </Button>
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}









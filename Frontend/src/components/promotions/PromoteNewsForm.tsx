// Frontend/src/components/promotions/PromoteNewsForm.tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  createNewsPromotion,
  type CreateNewsPromotionRequest,
} from "@/lib/api/promotions";
import { loadStripe } from "@stripe/stripe-js";

interface Props {
  onSuccess: () => void;
  onCancel: () => void;
}

const DURATION_OPTIONS = [
  { value: 7, label: "7 days", price: "€20" },
  { value: 14, label: "14 days", price: "€35" },
  { value: 30, label: "30 days", price: "€55" },
];

export default function PromoteNewsForm({ onSuccess, onCancel }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<CreateNewsPromotionRequest>({
    title: "",
    content: "",
    url: "",
    image_url: "",
    duration_days: 7,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.content) {
      toast.error("Title and content are required");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createNewsPromotion(formData);
      
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Promote News</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, title: e.target.value }))
              }
              required
            />
          </div>

          <div>
            <Label htmlFor="content">Content *</Label>
            <Textarea
              id="content"
              value={formData.content}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, content: e.target.value }))
              }
              required
              rows={5}
            />
          </div>

          <div>
            <Label htmlFor="url">URL (optional)</Label>
            <Input
              id="url"
              type="url"
              value={formData.url}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, url: e.target.value }))
              }
            />
          </div>

          <div>
            <Label htmlFor="image_url">Image URL (optional)</Label>
            <Input
              id="image_url"
              type="url"
              value={formData.image_url}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, image_url: e.target.value }))
              }
            />
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















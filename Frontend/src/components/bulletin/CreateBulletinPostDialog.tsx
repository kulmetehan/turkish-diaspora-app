// Frontend/src/components/bulletin/CreateBulletinPostDialog.tsx
import { LoginPrompt } from "@/components/auth/LoginPrompt";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useUserAuth } from "@/hooks/useUserAuth";
import { createBulletinPost } from "@/lib/api/bulletin";
import type { BulletinCategory, BulletinPostCreate } from "@/types/bulletin";
import { useState } from "react";
import { toast } from "sonner";

interface CreateBulletinPostDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const categoryOptions: { value: BulletinCategory; label: string }[] = [
  { value: "personnel_wanted", label: "Personeel gezocht" },
  { value: "offer", label: "Aanbieding" },
  { value: "free_for_sale", label: "Gratis/Te koop" },
  { value: "event", label: "Evenement" },
  { value: "services", label: "Diensten" },
  { value: "other", label: "Overig" },
];

export function CreateBulletinPostDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateBulletinPostDialogProps) {
  const { isAuthenticated } = useUserAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<Partial<BulletinPostCreate>>({
    title: "",
    description: "",
    category: "other",
    creator_type: "user",
    show_contact_info: true,
    expires_in_days: 7,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!formData.title || formData.title.length < 3) {
      toast.error("Titel moet minimaal 3 tekens bevatten");
      return;
    }

    if (formData.description && formData.description.length > 2000) {
      toast.error("Beschrijving mag maximaal 2000 tekens bevatten");
      return;
    }

    if (!formData.category) {
      toast.error("Selecteer een categorie");
      return;
    }

    if (!formData.show_contact_info && !formData.contact_phone && !formData.contact_email && !formData.contact_whatsapp) {
      toast.error("Geef minimaal één contactmethode op of schakel contactinformatie uit");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: BulletinPostCreate = {
        title: formData.title!,
        description: formData.description || undefined,
        category: formData.category!,
        creator_type: formData.creator_type || "user",
        business_id: formData.business_id,
        linked_location_id: formData.linked_location_id,
        city: formData.city || undefined,
        neighborhood: formData.neighborhood || undefined,
        contact_phone: formData.contact_phone || undefined,
        contact_email: formData.contact_email || undefined,
        contact_whatsapp: formData.contact_whatsapp || undefined,
        show_contact_info: formData.show_contact_info ?? true,
        image_urls: formData.image_urls || [],
        expires_in_days: formData.expires_in_days || 7,
      };

      const result = await createBulletinPost(payload);

      if (result.moderation_message) {
        toast.success("Advertentie ingediend", {
          description: result.moderation_message,
        });
      } else {
        toast.success("Advertentie gepubliceerd!");
      }

      // Reset form
      setFormData({
        title: "",
        description: "",
        category: "other",
        creator_type: "user",
        show_contact_info: true,
        expires_in_days: 7,
      });

      onOpenChange(false);
      onSuccess?.();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || "Kon advertentie niet plaatsen";

      if (typeof errorMsg === "object" && errorMsg.message) {
        toast.error(errorMsg.message, {
          description: errorMsg.details,
        });
      } else {
        toast.error("Fout", {
          description: typeof errorMsg === "string" ? errorMsg : "Er is een fout opgetreden",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Plaats advertentie</DialogTitle>
          <DialogDescription>
            Deel je advertentie met de Turkish diaspora gemeenschap in Nederland
          </DialogDescription>
        </DialogHeader>

        {!isAuthenticated ? (
          <div className="py-4">
            <LoginPrompt message="Log in om een advertentie te plaatsen" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div>
              <Label htmlFor="title">Titel *</Label>
              <Input
                id="title"
                value={formData.title || ""}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Bijv. Personeel gezocht voor bakkerij"
                maxLength={100}
                required
              />
              <p className="text-xs text-muted-foreground mt-1">
                {formData.title?.length || 0}/100 tekens
              </p>
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="description">Beschrijving</Label>
              <Textarea
                id="description"
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Geef meer details over je advertentie..."
                maxLength={2000}
                rows={4}
              />
              <p className="text-xs text-muted-foreground mt-1">
                {formData.description?.length || 0}/2000 tekens
              </p>
            </div>

            {/* Category */}
            <div>
              <Label htmlFor="category">Categorie *</Label>
              <Select
                value={formData.category}
                onValueChange={(value) =>
                  setFormData({ ...formData, category: value as BulletinCategory })
                }
              >
                <SelectTrigger id="category">
                  <SelectValue placeholder="Selecteer categorie" />
                </SelectTrigger>
                <SelectContent>
                  {categoryOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* City */}
            <div>
              <Label htmlFor="city">Stad (optioneel)</Label>
              <Input
                id="city"
                value={formData.city || ""}
                onChange={(e) => setFormData({ ...formData, city: e.target.value || undefined })}
                placeholder="Bijv. Rotterdam"
              />
            </div>

            {/* Contact Info */}
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <Label htmlFor="show_contact">Contactinformatie tonen</Label>
                <Switch
                  id="show_contact"
                  checked={formData.show_contact_info ?? true}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, show_contact_info: checked })
                  }
                />
              </div>

              {formData.show_contact_info && (
                <div className="space-y-3 pl-4 border-l-2 border-border">
                  <div>
                    <Label htmlFor="phone">Telefoon (optioneel)</Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={formData.contact_phone || ""}
                      onChange={(e) =>
                        setFormData({ ...formData, contact_phone: e.target.value || undefined })
                      }
                      placeholder="+31 6 12345678"
                    />
                  </div>

                  <div>
                    <Label htmlFor="email">E-mail (optioneel)</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.contact_email || ""}
                      onChange={(e) =>
                        setFormData({ ...formData, contact_email: e.target.value || undefined })
                      }
                      placeholder="voorbeeld@email.com"
                    />
                  </div>

                  <div>
                    <Label htmlFor="whatsapp">WhatsApp (optioneel)</Label>
                    <Input
                      id="whatsapp"
                      value={formData.contact_whatsapp || ""}
                      onChange={(e) =>
                        setFormData({ ...formData, contact_whatsapp: e.target.value || undefined })
                      }
                      placeholder="+31 6 12345678"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Expiry */}
            <div>
              <Label htmlFor="expires_in_days">Geldig voor (dagen)</Label>
              <Input
                id="expires_in_days"
                type="number"
                min="1"
                max="365"
                value={formData.expires_in_days || 7}
                onChange={(e) =>
                  setFormData({ ...formData, expires_in_days: parseInt(e.target.value) || 7 })
                }
              />
              <p className="text-xs text-muted-foreground mt-1">
                Standaard 7 dagen. Maximaal 365 dagen.
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Annuleren
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Plaatsen..." : "Advertentie plaatsen"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}


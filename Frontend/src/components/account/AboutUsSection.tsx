// Frontend/src/components/account/AboutUsSection.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Icon } from "@/components/Icon";
import { submitContactForm } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/ui/cn";

export function AboutUsSection({ className }: { className?: string }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!name.trim()) {
      toast.error("Naam is verplicht");
      return;
    }

    if (!email.trim() && !phone.trim()) {
      toast.error("Email of telefoonnummer is verplicht");
      return;
    }

    if (!message.trim()) {
      toast.error("Bericht is verplicht");
      return;
    }

    if (message.length > 1000) {
      toast.error("Bericht mag maximaal 1000 tekens bevatten");
      return;
    }

    setIsSubmitting(true);
    try {
      await submitContactForm({
        name: name.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        message: message.trim(),
      });

      setIsSubmitted(true);
      setName("");
      setEmail("");
      setPhone("");
      setMessage("");
      toast.success("Bericht verzonden! We nemen zo snel mogelijk contact met je op.");
    } catch (err: any) {
      toast.error("Kon bericht niet verzenden", {
        description: err.message || "Er is een fout opgetreden",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className={cn("space-y-4", className)}>
        <div className="rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-6 text-center">
          <Icon name="CheckCircle" className="h-12 w-12 mx-auto mb-4 text-green-600 dark:text-green-400" />
          <h3 className="text-lg font-gilroy font-semibold text-green-900 dark:text-green-100 mb-2">
            Bericht verzonden!
          </h3>
          <p className="text-sm text-green-700 dark:text-green-300">
            Bedankt voor je bericht. We nemen zo snel mogelijk contact met je op.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSubmitted(false)}
            className="mt-4"
          >
            Nieuw bericht versturen
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* About Turkspot */}
      <div className="space-y-4">
        <h2 className="text-lg font-gilroy font-medium text-foreground">Over Turkspot</h2>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>
            Turkspot is een platform dat de Turkse gemeenschap in Nederland helpt om lokale bedrijven, 
            restaurants en diensten te ontdekken. We maken gebruik van AI-technologie om een uitgebreide 
            kaart te creëren van Turkse gemeenschapslocaties door heel Nederland.
          </p>
          <p>
            Ons doel is om de Turkse diaspora te verbinden en te ondersteunen door het delen van kennis 
            over lokale bedrijven en diensten. We geloven dat een sterke gemeenschap begint bij het 
            vinden en ondersteunen van elkaar.
          </p>
          <p>
            Turkspot wordt continu verbeterd met nieuwe functies en updates om de beste ervaring te 
            bieden voor onze gebruikers.
          </p>
        </div>
      </div>

      {/* Contact Information */}
      <div className="space-y-4">
        <h2 className="text-lg font-gilroy font-medium text-foreground">Contact</h2>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p>
            Heb je vragen, suggesties of wil je samenwerken? Aarzel niet om contact met ons op te nemen. 
            We staan open voor alle soorten vragen en eventuele samenwerkingen.
          </p>
        </div>
      </div>

      {/* Contact Form */}
      <Card className="p-6">
        <h3 className="text-lg font-gilroy font-semibold text-foreground mb-4">
          Stuur ons een bericht
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="contact-name">Naam *</Label>
            <Input
              id="contact-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Je naam"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="contact-email">Email</Label>
            <Input
              id="contact-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="je@email.nl"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="contact-phone">Telefoonnummer</Label>
            <Input
              id="contact-phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="06 12345678"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="contact-message">Bericht *</Label>
            <Textarea
              id="contact-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Je bericht..."
              required
              maxLength={1000}
              rows={6}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              {message.length}/1000 tekens
            </p>
          </div>

          <div className="text-xs text-muted-foreground">
            * Verplichte velden. Minimaal email of telefoonnummer is vereist.
          </div>

          <Button
            type="submit"
            disabled={isSubmitting || !name.trim() || !message.trim() || (!email.trim() && !phone.trim())}
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Icon name="Loader2" className="h-4 w-4 mr-2 animate-spin" />
                Verzenden...
              </>
            ) : (
              <>
                <Icon name="Send" className="h-4 w-4 mr-2" />
                Verzenden
              </>
            )}
          </Button>
        </form>
      </Card>
    </div>
  );
}








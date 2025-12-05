// Frontend/src/components/settings/PrivacySettings.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { getPrivacySettings, updatePrivacySettings, type PrivacySettings as PrivacySettingsType } from "@/lib/api";

export function PrivacySettings() {
  const [settings, setSettings] = useState<PrivacySettingsType>({
    allow_location_tracking: true,
    allow_push_notifications: false,
    allow_email_digest: false,
    data_retention_consent: true,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setIsLoading(true);
      const data = await getPrivacySettings();
      setSettings(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon privacy instellingen niet laden";
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = async (field: keyof PrivacySettingsType, value: boolean) => {
    const newSettings = { ...settings, [field]: value };
    setSettings(newSettings);

    try {
      setIsSaving(true);
      await updatePrivacySettings({ [field]: value });
      toast.success("Privacy instellingen bijgewerkt");
    } catch (err) {
      // Revert on error
      setSettings(settings);
      const message = err instanceof Error ? err.message : "Kon privacy instellingen niet bijwerken";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Privacy instellingen laden...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Privacy Instellingen</CardTitle>
        <CardDescription>
          Beheer hoe je gegevens worden gebruikt en gedeeld
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <Checkbox
              id="allow_location_tracking"
              checked={settings.allow_location_tracking}
              onChange={(e) => handleUpdate("allow_location_tracking", e.target.checked)}
              disabled={isSaving}
            />
            <div className="flex-1">
              <Label htmlFor="allow_location_tracking" className="cursor-pointer">
                Locatie tracking toestaan
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Sta toe dat we je locatie gebruiken voor nearby features en personalized content
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Checkbox
              id="allow_push_notifications"
              checked={settings.allow_push_notifications}
              onChange={(e) => handleUpdate("allow_push_notifications", e.target.checked)}
              disabled={isSaving}
            />
            <div className="flex-1">
              <Label htmlFor="allow_push_notifications" className="cursor-pointer">
                Push notificaties toestaan
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Ontvang meldingen over nieuwe polls, trending locaties en activiteit
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Checkbox
              id="allow_email_digest"
              checked={settings.allow_email_digest}
              onChange={(e) => handleUpdate("allow_email_digest", e.target.checked)}
              disabled={isSaving}
            />
            <div className="flex-1">
              <Label htmlFor="allow_email_digest" className="cursor-pointer">
                Wekelijkse email digest
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Ontvang wekelijks een samenvatting van trending locaties en activiteit
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Checkbox
              id="data_retention_consent"
              checked={settings.data_retention_consent}
              onChange={(e) => handleUpdate("data_retention_consent", e.target.checked)}
              disabled={isSaving}
            />
            <div className="flex-1">
              <Label htmlFor="data_retention_consent" className="cursor-pointer">
                Data retentie toestemming
              </Label>
              <p className="text-xs text-muted-foreground mt-1">
                Toestemming om je gegevens te bewaren volgens ons privacybeleid
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Voor meer informatie, bekijk ons{" "}
            <a href="#/privacy" className="underline hover:text-foreground">
              privacybeleid
            </a>
            .
          </p>
        </div>
      </CardContent>
    </Card>
  );
}



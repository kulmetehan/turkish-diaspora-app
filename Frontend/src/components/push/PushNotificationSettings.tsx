// Frontend/src/components/push/PushNotificationSettings.tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useUserAuth } from "@/hooks/useUserAuth";
import { Icon } from "@/components/Icon";
import { 
  getPushPreferences, 
  updatePushPreferences,
  registerDeviceToken,
  type PushPreferences,
} from "@/lib/api";
import { initializePushNotifications } from "@/lib/push";
import { toast } from "sonner";

export function PushNotificationSettings() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useUserAuth();
  const [preferences, setPreferences] = useState<PushPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadPreferences();
      // Don't auto-request permission - let user do it explicitly
    } else {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const prefs = await getPushPreferences();
      setPreferences(prefs);
    } catch (err) {
      toast.error("Kon voorkeuren niet laden");
    } finally {
      setLoading(false);
    }
  };

  const registerForPush = async () => {
    if (!isAuthenticated) {
      toast.error("Je moet ingelogd zijn om push notificaties in te schakelen");
      navigate("/auth");
      return;
    }

    setRegistering(true);
    try {
      // Check browser support
      if (!("Notification" in window) || !("serviceWorker" in navigator)) {
        toast.error("Push notifications worden niet ondersteund in deze browser");
        return;
      }

      // Request permission first
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        toast.error("Notificatie toestemming geweigerd");
        return;
      }

      // Get VAPID public key from environment
      const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
      if (!vapidPublicKey) {
        toast.error("Push notifications zijn niet geconfigureerd");
        return;
      }
      
      const { registration, subscription } = await initializePushNotifications(vapidPublicKey);
      
      if (!subscription) {
        toast.error("Kon je niet abonneren op push notificaties");
        return;
      }

      // Convert subscription to JSON for backend
      const subscriptionJson = JSON.stringify({
        endpoint: subscription.endpoint,
        keys: subscription.keys,
      });

      await registerDeviceToken({
        token: subscriptionJson,
        platform: "web",
        user_agent: navigator.userAgent,
      });

      toast.success("Push notifications ingeschakeld");
      loadPreferences(); // Reload preferences
    } catch (err) {
      toast.error("Kon push notificaties niet registreren", {
        description: err instanceof Error ? err.message : "Onbekende fout",
      });
    } finally {
      setRegistering(false);
    }
  };

  const handleToggle = async (field: keyof PushPreferences, value: boolean) => {
    if (!isAuthenticated) {
      toast.error("Je moet ingelogd zijn om instellingen te wijzigen");
      navigate("/auth");
      return;
    }

    if (!preferences) return;

    const update = { [field]: value };
    try {
      const updated = await updatePushPreferences(update);
      setPreferences(updated);
      toast.success("Voorkeuren bijgewerkt");
    } catch (err) {
      toast.error("Kon voorkeuren niet bijwerken");
    }
  };

  if (authLoading || loading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!isAuthenticated) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Push Notificaties</CardTitle>
          <CardDescription>
            Ontvang meldingen op je apparaat
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center border border-dashed border-border rounded-lg bg-muted/30">
            <Icon name="Bell" className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Inloggen vereist</h3>
            <p className="text-sm text-muted-foreground mb-6 max-w-md">
              Om push notificaties te ontvangen, heb je een account nodig. 
              Dit zorgt ervoor dat we notificaties alleen naar jouw geregistreerde apparaten sturen.
            </p>
            <Button onClick={() => navigate("/auth")} className="inline-flex items-center gap-2">
              <Icon name="LogIn" className="h-4 w-4" />
              <span>Inloggen / Registreren</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!preferences) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Push Notificaties</CardTitle>
        <CardDescription>
          Beheer je notificatie voorkeuren
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="enabled">Push notificaties inschakelen</Label>
            <p className="text-sm text-muted-foreground">
              Ontvang meldingen op dit apparaat
            </p>
          </div>
          <Switch
            id="enabled"
            checked={preferences.enabled}
            onCheckedChange={(checked) => handleToggle("enabled", checked)}
          />
        </div>

        {preferences.enabled && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="poll">Poll Notificaties</Label>
                <p className="text-sm text-muted-foreground">
                  Ontvang meldingen over nieuwe polls
                </p>
              </div>
              <Switch
                id="poll"
                checked={preferences.poll_notifications}
                onCheckedChange={(checked) => handleToggle("poll_notifications", checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="trending">Trending Notificaties</Label>
                <p className="text-sm text-muted-foreground">
                  Ontvang meldingen wanneer je favorieten trending zijn
                </p>
              </div>
              <Switch
                id="trending"
                checked={preferences.trending_notifications}
                onCheckedChange={(checked) => handleToggle("trending_notifications", checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="activity">Activiteit Notificaties</Label>
                <p className="text-sm text-muted-foreground">
                  Ontvang meldingen over activiteit op je content
                </p>
              </div>
              <Switch
                id="activity"
                checked={preferences.activity_notifications}
                onCheckedChange={(checked) => handleToggle("activity_notifications", checked)}
              />
            </div>
          </>
        )}

        {!preferences.enabled && (
          <Button onClick={registerForPush} disabled={registering} className="w-full">
            {registering ? "Registreren..." : "Push Notificaties Inschakelen"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}


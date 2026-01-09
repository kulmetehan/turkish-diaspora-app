// Frontend/src/components/push/PushNotificationSettings.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
  getPushPreferences,
  registerDeviceToken,
  updatePushPreferences,
  type PushPreferences,
} from "@/lib/api";
import { initializePushNotifications } from "@/lib/push";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
        console.error("Push notification support check failed:", {
          hasNotification: "Notification" in window,
          hasServiceWorker: "serviceWorker" in navigator,
        });
        return;
      }

      // Check HTTPS (required for push notifications)
      if (location.protocol !== "https:" && location.hostname !== "localhost") {
        toast.error("Push notifications vereisen HTTPS. De app moet via HTTPS worden geladen.");
        console.error("HTTPS required for push notifications");
        return;
      }

      // Get VAPID public key from environment
      const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
      if (!vapidPublicKey) {
        toast.error("Push notifications zijn niet geconfigureerd (VAPID key ontbreekt)");
        console.error("VAPID public key missing from environment variables");
        return;
      }

      console.log("Starting push notification registration...");

      // Check service worker registration first
      let registration: ServiceWorkerRegistration | null = null;
      try {
        registration = await navigator.serviceWorker.ready;
        console.log("Service worker ready:", registration.scope);
      } catch (error) {
        console.error("Service worker not ready, attempting to register:", error);
        // Try to register service worker
        const { registerServiceWorker } = await import("@/lib/push");
        registration = await registerServiceWorker();
        if (!registration) {
          toast.error("Service worker kon niet worden geregistreerd. Probeer de pagina te vernieuwen.");
          console.error("Service worker registration failed");
          return;
        }
      }

      // Request permission
      console.log("Requesting notification permission...");
      const permission = await Notification.requestPermission();
      console.log("Notification permission:", permission);
      
      if (permission !== "granted") {
        toast.error(`Notificatie toestemming geweigerd (status: ${permission})`);
        return;
      }

      // Initialize push notifications (skip permission check since we already did it)
      console.log("Initializing push notifications with VAPID key...");
      const { registration: pushRegistration, subscription } = await initializePushNotifications(vapidPublicKey, true);

      if (!pushRegistration) {
        toast.error("Service worker kon niet worden gebruikt voor push notificaties");
        console.error("Push registration failed: no service worker registration");
        return;
      }

      if (!subscription) {
        toast.error("Kon je niet abonneren op push notificaties");
        console.error("Push subscription failed: no subscription returned");
        return;
      }

      console.log("Push subscription created:", {
        endpoint: subscription.endpoint.substring(0, 50) + "...",
        hasKeys: !!subscription.keys,
      });

      // Convert subscription to JSON for backend
      const subscriptionJson = JSON.stringify({
        endpoint: subscription.endpoint,
        keys: subscription.keys,
      });

      console.log("Registering device token with backend...");
      await registerDeviceToken({
        token: subscriptionJson,
        platform: "web",
        user_agent: navigator.userAgent,
      });

      console.log("Device token registered successfully");
      
      // Automatically enable push notifications after successful registration
      // This ensures the UI updates immediately and the button disappears
      try {
        const updated = await updatePushPreferences({ enabled: true });
        setPreferences(updated);
        toast.success("Push notifications ingeschakeld");
      } catch (err) {
        // If updating preferences fails, still reload them
        console.warn("Failed to update preferences, reloading...", err);
        await loadPreferences();
        toast.success("Push notifications geregistreerd");
      }
    } catch (err) {
      console.error("Push notification registration error:", err);
      
      // Show more specific error messages
      let errorMessage = "Kon push notificaties niet registreren";
      if (err instanceof Error) {
        errorMessage = err.message;
        
        // Handle specific error types
        if (err.name === "NotAllowedError" || err.message.includes("permission")) {
          errorMessage = "Notificatie toestemming is geweigerd. Controleer je browser instellingen.";
        } else if (err.message.includes("VAPID")) {
          errorMessage = "VAPID key configuratie fout. Neem contact op met de beheerder.";
        } else if (err.message.includes("Service worker")) {
          errorMessage = "Service worker probleem. Probeer de pagina te vernieuwen.";
        } else if (err.message.includes("HTTPS")) {
          errorMessage = "Push notifications vereisen HTTPS.";
        }
      }
      
      toast.error(errorMessage, {
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

    // Optimistically update UI
    const previousValue = preferences[field];
    setPreferences({ ...preferences, [field]: value });

    const update = { [field]: value };
    try {
      const updated = await updatePushPreferences(update);
      setPreferences(updated);
      
      // Only show toast for non-enabled toggles (enabled toggle is handled by registerForPush)
      if (field !== "enabled") {
        toast.success("Voorkeuren bijgewerkt");
      }
    } catch (err) {
      // Revert on error
      setPreferences({ ...preferences, [field]: previousValue });
      toast.error("Kon voorkeuren niet bijwerken");
      console.error("Failed to update push preferences:", err);
    }
  };

  if (authLoading || loading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!isAuthenticated) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-gilroy font-medium text-foreground mb-1">Push Notificaties</h2>
          <p className="text-sm text-muted-foreground">
            Ontvang meldingen op je apparaat
          </p>
        </div>
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
      </div>
    );
  }

  if (!preferences) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-gilroy font-medium text-foreground mb-1">Push Notificaties</h2>
        <p className="text-sm text-muted-foreground">
          Beheer je notificatie voorkeuren
        </p>
      </div>
      <div className="flex items-center justify-between">
        <div>
          <Label htmlFor="enabled">Push notificaties inschakelen</Label>
          <p className="text-sm text-muted-foreground">
            {preferences.enabled 
              ? "Push notifications zijn actief op dit apparaat" 
              : "Ontvang meldingen op dit apparaat"}
          </p>
        </div>
        <Switch
          id="enabled"
          checked={preferences.enabled}
          onCheckedChange={(checked) => handleToggle("enabled", checked)}
          disabled={registering}
        />
      </div>
      
      {preferences.enabled && (
        <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
          <Icon name="CheckCircle" className="h-5 w-5 text-green-500" />
          <p className="text-sm text-green-700 dark:text-green-400">
            Push notifications zijn actief. Je ontvangt meldingen op dit apparaat.
          </p>
        </div>
      )}

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

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="chat">Chat Notificaties</Label>
              <p className="text-sm text-muted-foreground">
                Ontvang meldingen wanneer je nieuwe chat berichten krijgt
              </p>
            </div>
            <Switch
              id="chat"
              checked={preferences.chat_notifications ?? true}
              onCheckedChange={(checked) => handleToggle("chat_notifications", checked)}
            />
          </div>
        </>
      )}

      {!preferences.enabled && (
        <Button 
          onClick={registerForPush} 
          disabled={registering || loading} 
          className="w-full"
        >
          {registering ? (
            <>
              <span className="animate-spin mr-2">⏳</span>
              Registreren...
            </>
          ) : (
            "Push Notificaties Inschakelen"
          )}
        </Button>
      )}
    </div>
  );
}


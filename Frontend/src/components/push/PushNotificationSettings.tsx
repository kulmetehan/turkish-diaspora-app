// Frontend/src/components/push/PushNotificationSettings.tsx
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  getPushPreferences, 
  updatePushPreferences,
  registerDeviceToken,
  type PushPreferences,
} from "@/lib/api";
import { initializePushNotifications } from "@/lib/push";
import { toast } from "sonner";

export function PushNotificationSettings() {
  const [preferences, setPreferences] = useState<PushPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);

  useEffect(() => {
    loadPreferences();
    requestPermission();
  }, []);

  const loadPreferences = async () => {
    try {
      const prefs = await getPushPreferences();
      setPreferences(prefs);
    } catch (err) {
      toast.error("Failed to load preferences");
    } finally {
      setLoading(false);
    }
  };

  const requestPermission = async () => {
    if ("Notification" in window && "serviceWorker" in navigator) {
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        await registerForPush();
      }
    }
  };

  const registerForPush = async () => {
    setRegistering(true);
    try {
      // Get VAPID public key from environment (would be set via env var)
      const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
      
      const { registration, subscription } = await initializePushNotifications(vapidPublicKey);
      
      if (!subscription) {
        toast.error("Failed to subscribe to push notifications");
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

      toast.success("Push notifications enabled");
      loadPreferences(); // Reload preferences
    } catch (err) {
      toast.error("Failed to register for push notifications", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRegistering(false);
    }
  };

  const handleToggle = async (field: keyof PushPreferences, value: boolean) => {
    if (!preferences) return;

    const update = { [field]: value };
    try {
      const updated = await updatePushPreferences(update);
      setPreferences(updated);
      toast.success("Preferences updated");
    } catch (err) {
      toast.error("Failed to update preferences");
    }
  };

  if (loading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!preferences) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Push Notification Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="enabled">Enable Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Receive push notifications on this device
            </p>
          </div>
          <Switch
            id="enabled"
            checked={preferences.enabled}
            onCheckedChange={(checked) => handleToggle("enabled", checked)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="poll">Poll Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Get notified about new polls
            </p>
          </div>
          <Switch
            id="poll"
            checked={preferences.poll_notifications}
            onCheckedChange={(checked) => handleToggle("poll_notifications", checked)}
            disabled={!preferences.enabled}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="trending">Trending Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Get notified when your favorites are trending
            </p>
          </div>
          <Switch
            id="trending"
            checked={preferences.trending_notifications}
            onCheckedChange={(checked) => handleToggle("trending_notifications", checked)}
            disabled={!preferences.enabled}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="activity">Activity Notifications</Label>
            <p className="text-sm text-muted-foreground">
              Get notified about activity on your content
            </p>
          </div>
          <Switch
            id="activity"
            checked={preferences.activity_notifications}
            onCheckedChange={(checked) => handleToggle("activity_notifications", checked)}
            disabled={!preferences.enabled}
          />
        </div>

        {!preferences.enabled && (
          <Button onClick={registerForPush} disabled={registering} className="w-full">
            {registering ? "Registering..." : "Enable Push Notifications"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}


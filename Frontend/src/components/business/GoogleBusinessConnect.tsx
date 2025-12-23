// Frontend/src/components/business/GoogleBusinessConnect.tsx
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  initiateGoogleBusinessConnect,
  triggerGoogleBusinessSync,
  getGoogleBusinessStatus,
  type GoogleBusinessSyncStatus,
} from "@/lib/api";
import { toast } from "sonner";

interface GoogleBusinessConnectProps {
  locationId: number;
}

export function GoogleBusinessConnect({ locationId }: GoogleBusinessConnectProps) {
  const [status, setStatus] = useState<GoogleBusinessSyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    loadStatus();
  }, [locationId]);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const data = await getGoogleBusinessStatus();
      const locationStatus = data.locations.find(loc => loc.location_id === locationId);
      setStatus(locationStatus || null);
    } catch (err) {
      toast.error("Failed to load sync status");
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const result = await initiateGoogleBusinessConnect(locationId);
      // Redirect to OAuth URL
      window.location.href = result.oauth_url;
    } catch (err) {
      toast.error("Failed to initiate connection", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
      setConnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await triggerGoogleBusinessSync(locationId);
      toast.success("Sync triggered successfully");
      // Reload status after a delay
      setTimeout(() => {
        loadStatus();
      }, 2000);
    } catch (err) {
      toast.error("Failed to trigger sync", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <Skeleton className="h-32 w-full" />;
  }

  const isConnected = status?.sync_status === "synced" || status?.sync_status === "pending";
  const hasError = status?.sync_status === "error";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Google Business Sync</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected ? (
          <div>
            <p className="text-sm text-muted-foreground mb-4">
              Connect your Google Business Profile to automatically sync business information.
            </p>
            <Button onClick={handleConnect} disabled={connecting}>
              {connecting ? "Connecting..." : "Connect Google Business"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium">Status: {status.sync_status}</p>
              {status.last_synced_at && (
                <p className="text-sm text-muted-foreground">
                  Last synced: {new Date(status.last_synced_at).toLocaleString()}
                </p>
              )}
              {hasError && status.sync_error && (
                <p className="text-sm text-destructive mt-2">
                  Error: {status.sync_error}
                </p>
              )}
            </div>
            
            <Button onClick={handleSync} disabled={syncing}>
              {syncing ? "Syncing..." : "Sync Now"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


























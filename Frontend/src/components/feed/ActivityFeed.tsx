// Frontend/src/components/feed/ActivityFeed.tsx
import { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/ui/cn";
import { getActivityFeed, type ActivityItem } from "@/lib/api";
import { ActivityCard } from "./ActivityCard";
import { LoginPrompt } from "@/components/auth/LoginPrompt";
import { useUserAuth } from "@/hooks/useUserAuth";
import { toast } from "sonner";

// Helper function to get Dutch label for activity type
function getActivityTypeLabel(activityType: ActivityItem["activity_type"]): string {
  const labels: Record<ActivityItem["activity_type"], string> = {
    check_in: "check-in",
    reaction: "reactie",
    note: "notitie",
    poll_response: "poll",
    favorite: "favoriet",
    bulletin_post: "advertentie",
  };
  return labels[activityType] || activityType;
}

interface ActivityFeedProps {
  className?: string;
  activityType?: ActivityItem["activity_type"];
}

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

export function ActivityFeed({ className, activityType }: ActivityFeedProps) {
  const { isAuthenticated } = useUserAuth();
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getActivityFeed(INITIAL_LIMIT, 0, activityType);
      setItems(data);
      setOffset(data.length);
      setHasMore(data.length >= INITIAL_LIMIT);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon activiteit niet laden";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [activityType]);

  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);
    try {
      const data = await getActivityFeed(LOAD_MORE_LIMIT, offset, activityType);
      if (data.length > 0) {
        setItems((prev) => [...prev, ...data]);
        setOffset((prev) => prev + data.length);
        setHasMore(data.length >= LOAD_MORE_LIMIT);
      } else {
        setHasMore(false);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon meer activiteit niet laden";
      toast.error(message);
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMore, offset, activityType]);

  useEffect(() => {
    // Reset state when activityType changes
    setItems([]);
    setOffset(0);
    setHasMore(true);
    loadInitialData();
  }, [loadInitialData]);

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-xl border border-border/80 bg-card p-4">
            <div className="flex items-start gap-3">
              <Skeleton className="h-5 w-5 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("rounded-xl border border-border/80 bg-card p-5 text-center shadow-soft", className)}>
        <p className="text-foreground">{error}</p>
        <Button
          size="sm"
          className="mt-4"
          onClick={loadInitialData}
          variant="outline"
        >
          Opnieuw proberen
        </Button>
      </div>
    );
  }

  if (items.length === 0) {
    // Show login prompt if user is not authenticated (they might have activity that requires login)
    if (!isAuthenticated) {
      const loginMessage = activityType
        ? activityType === "check_in"
          ? "Log in om je check-ins te zien"
          : activityType === "note"
          ? "Log in om je notities te zien"
          : `Log in om je ${getActivityTypeLabel(activityType)} activiteit te zien`
        : "Log in om je activiteit te zien";
      return (
        <div className={cn("", className)}>
          <LoginPrompt message={loginMessage} />
        </div>
      );
    }

    // If authenticated, show empty state message
    const emptyMessage = activityType
      ? `Geen ${getActivityTypeLabel(activityType)} activiteit gevonden.`
      : "Er is nog geen activiteit. Begin met check-ins, reacties of notities!";
    return (
      <div className={cn("rounded-xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-soft", className)}>
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {items.map((item) => (
        <ActivityCard key={item.id} item={item} />
      ))}
      {hasMore && (
        <div className="flex justify-center pt-2">
          {isLoadingMore ? (
            <p className="text-sm text-muted-foreground">Meer activiteit laden…</p>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={loadMore}
              className="border-border text-foreground hover:bg-muted"
            >
              Meer laden
            </Button>
          )}
        </div>
      )}
    </div>
  );
}




// Frontend/src/components/activity/ActivityHistory.tsx
import { ActivityCard } from "@/components/feed/ActivityCard";
import { ActivityFeed } from "@/components/feed/ActivityFeed";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getActivityFeed, type ActivityItem } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { format, isToday, isWithinInterval, isYesterday, parseISO, startOfWeek } from "date-fns";
import { nl } from "date-fns/locale";
import { useCallback, useEffect, useState } from "react";

interface ActivityHistoryProps {
  className?: string;
}

type ActivityFilter = "all" | "check_in" | "reaction" | "note" | "poll_response" | "favorite";

export function ActivityHistory({ className }: ActivityHistoryProps) {
  const [filter, setFilter] = useState<ActivityFilter>("all");

  // For now, we use the existing ActivityFeed component
  // In the future, we could add client-side filtering or a filtered API endpoint

  return (
    <div className={cn("space-y-4", className)}>
      <Tabs value={filter} onValueChange={(value) => setFilter(value as ActivityFilter)}>
        <div className="max-w-full overflow-x-auto mb-4" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>
          <TabsList className="bg-card">
            <TabsTrigger value="all">Alles</TabsTrigger>
            <TabsTrigger value="check_in">Check-ins</TabsTrigger>
            <TabsTrigger value="reaction">Reacties</TabsTrigger>
            <TabsTrigger value="note">Notities</TabsTrigger>
            <TabsTrigger value="poll_response">Polls</TabsTrigger>
            <TabsTrigger value="favorite">Favorieten</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="all">
          <ActivityFeed />
        </TabsContent>

        <TabsContent value="check_in">
          <FilteredActivityFeed activityType="check_in" />
        </TabsContent>

        <TabsContent value="reaction">
          <FilteredActivityFeed activityType="reaction" />
        </TabsContent>

        <TabsContent value="note">
          <FilteredActivityFeed activityType="note" />
        </TabsContent>

        <TabsContent value="poll_response">
          <FilteredActivityFeed activityType="poll_response" />
        </TabsContent>

        <TabsContent value="favorite">
          <FilteredActivityFeed activityType="favorite" />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Component that filters activity by type
function FilteredActivityFeed({ activityType }: { activityType: ActivityItem["activity_type"] }) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  const INITIAL_LIMIT = 20;
  const LOAD_MORE_LIMIT = 20;

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
      // Silently fail on load more
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMore, offset, activityType]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  if (isLoading) {
    return (
      <div className="text-sm text-muted-foreground p-4 rounded-xl border border-border/80 bg-card">
        <p>Activiteit laden...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-destructive p-4 rounded-xl border border-border/80 bg-card">
        <p>Fout: {error}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 rounded-xl border border-border/80 bg-card">
        <p>Geen {activityType} activiteit gevonden.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <ActivityCard key={item.id} item={item} />
      ))}
      {hasMore && (
        <Button
          variant="outline"
          onClick={loadMore}
          disabled={isLoadingMore}
          className="w-full"
        >
          {isLoadingMore ? "Laden..." : "Meer laden"}
        </Button>
      )}
    </div>
  );
}

// Helper function to group activities by date (for future use)
function groupActivitiesByDate(items: ActivityItem[]): Record<string, ActivityItem[]> {
  const groups: Record<string, ActivityItem[]> = {};

  for (const item of items) {
    const date = parseISO(item.created_at);
    let groupKey: string;

    if (isToday(date)) {
      groupKey = "Vandaag";
    } else if (isYesterday(date)) {
      groupKey = "Gisteren";
    } else if (isWithinInterval(date, { start: startOfWeek(date), end: new Date() })) {
      groupKey = "Deze week";
    } else {
      groupKey = format(date, "d MMMM yyyy", { locale: nl });
    }

    if (!groups[groupKey]) {
      groups[groupKey] = [];
    }
    groups[groupKey].push(item);
  }

  return groups;
}


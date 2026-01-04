import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getUserActivity, type ActivityItem } from "@/lib/api";
import { FeedCard } from "@/components/feed/FeedCard";
import { transformActivityItem } from "@/pages/FeedPage";
import { useTranslation } from "@/hooks/useTranslation";
import { useNavigate } from "react-router-dom";

interface UserActivityFeedProps {
  userId: string;
  initialActivities: ActivityItem[];
  onUserClick?: (userId: string) => void;
}

export function UserActivityFeed({ userId, initialActivities, onUserClick }: UserActivityFeedProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activities, setActivities] = useState<ActivityItem[]>(initialActivities);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(initialActivities.length >= 10);
  
  const loadMore = async () => {
    setLoading(true);
    try {
      const more = await getUserActivity(userId, { limit: 10, offset: activities.length });
      if (more.length === 0) {
        setHasMore(false);
      } else {
        setActivities([...activities, ...more]);
        setHasMore(more.length >= 10);
      }
    } catch (error) {
      console.error("Failed to load more activities:", error);
    } finally {
      setLoading(false);
    }
  };
  
  if (activities.length === 0) {
    return (
      <div className="text-center py-4 text-sm text-muted-foreground">
        Geen recente activiteit
      </div>
    );
  }
  
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-gilroy font-medium text-foreground">Recente activiteit</h3>
      <div className="space-y-3">
        {activities.map((item) => {
          const cardProps = transformActivityItem(
            item,
            () => {}, // onReactionToggle - could be implemented later
            () => {}, // onBookmark - could be implemented later
            t,
            undefined, // onImageClick
            (locationId) => navigate(`/locations/${locationId}`),
            undefined, // onPollClick
            onUserClick, // onUserClick - allow opening other user profiles
          );
          return <FeedCard key={item.id} {...cardProps} />;
        })}
      </div>
      {hasMore && (
        <Button
          variant="outline"
          size="sm"
          onClick={loadMore}
          disabled={loading}
          className="w-full"
        >
          {loading ? "Laden..." : "Meer laden"}
        </Button>
      )}
    </div>
  );
}


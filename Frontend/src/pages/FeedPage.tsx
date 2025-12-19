// Frontend/src/pages/FeedPage.tsx
import { AppHeader } from "@/components/feed/AppHeader";
import { DashboardOverview } from "@/components/feed/DashboardOverview";
import type { FeedCardProps } from "@/components/feed/FeedCard";
import { FeedFilterTabs, type ActivityFilter } from "@/components/feed/FeedFilterTabs";
import { FeedList } from "@/components/feed/FeedList";
import { GreetingBlock } from "@/components/feed/GreetingBlock";
import { ImageModal } from "@/components/feed/ImageModal";
import { PollModal } from "@/components/feed/PollModal";
import { FooterTabs } from "@/components/FooterTabs";
import { AppViewportShell } from "@/components/layout";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { getActivityFeed, getActivityReactions, getCurrentUser, getOnboardingStatus, toggleActivityBookmark, toggleActivityReaction, type ActivityItem, type OnboardingStatus, type ReactionType } from "@/lib/api";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

// Helper function to get activity message (reused from ActivityCard logic)
function getActivityMessage(item: ActivityItem): string {
  const locationName = item.location_name || "een locatie";

  switch (item.activity_type) {
    case "check_in":
      return `heeft ingecheckt bij ${locationName}`;
    case "reaction":
      const reactionType = (item.payload?.reaction_type as string) || "🔥";
      const reactionEmoji: Record<string, string> = {
        fire: "🔥",
        heart: "❤️",
        thumbs_up: "👍",
        smile: "😊",
        star: "⭐",
        flag: "🚩",
      };
      const emoji = reactionEmoji[reactionType] || reactionType;
      return `reageerde met ${emoji} op ${locationName}`;
    case "note":
      return `schreef een notitie over ${locationName}`;
    case "poll_response":
      return `heeft gestemd op een poll`;
    case "favorite":
      return `heeft ${locationName} toegevoegd aan favorieten`;
    case "bulletin_post":
      const title = (item.payload?.title as string) || "";
      return `heeft een advertentie geplaatst: "${title}"`;
    case "event":
      return `heeft een event geplaatst: ${locationName}`;
    default:
      return `heeft activiteit op ${locationName}`;
  }
}

// Transform ActivityItem to FeedCardProps
function transformActivityItem(
  item: ActivityItem,
  onReactionToggle: (id: number, reactionType: ReactionType) => void,
  onBookmark: (id: number) => void,
  onClick: (item: ActivityItem) => void,
  onImageClick?: (imageUrl: string) => void,
  onLocationClick?: (locationId: number) => void,
  onPollClick?: (pollId: number) => void
): FeedCardProps {
  const noteContent = item.activity_type === "note"
    ? (item.payload?.note_preview as string) || (item.payload?.content as string) || null
    : null;

  const pollId = item.activity_type === "poll_response"
    ? (item.payload?.poll_id as number) || null
    : null;

  const transformed = {
    id: item.id,
    user: {
      avatar: item.user?.avatar_url || null,
      name: item.user?.name || "Iemand",
    },
    locationName: item.location_name || null,
    locationId: item.location_id || null,
    timestamp: item.created_at,
    contentText: getActivityMessage(item),
    noteContent,
    pollId,
    mediaUrl: item.media_url || undefined,
    likeCount: item.like_count,
    isLiked: item.is_liked,
    isBookmarked: item.is_bookmarked,
    reactions: item.reactions || null,
    userReaction: item.user_reaction || null,
    type: item.activity_type,
    isPromoted: item.is_promoted,
    onReactionToggle: (reactionType: ReactionType) => onReactionToggle(item.id, reactionType),
    onBookmark: () => onBookmark(item.id),
    onClick: () => onClick(item),
    onImageClick,
    onLocationClick,
    onPollClick,
  };

  // #region agent log
  if (item.reactions) {
    fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'FeedPage.tsx:101', message: 'transformActivityItem: reactions in transformed', data: { activityId: item.id, reactions: item.reactions, userReaction: item.user_reaction, transformedReactions: transformed.reactions }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'B' }) }).catch(() => { });
  }
  // #endregion

  return transformed;
}

export default function FeedPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // State management
  // Check if filter is passed via navigation state
  const initialFilter = (location.state as { filter?: ActivityFilter })?.filter || "all";
  const [activeFilter, setActiveFilter] = useState<ActivityFilter>(initialFilter);
  const [feedItems, setFeedItems] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const [userName, setUserName] = useState<string | null>(null);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [imageModalUrl, setImageModalUrl] = useState<string | null>(null);
  const [pollModalOpen, setPollModalOpen] = useState(false);
  const [pollModalId, setPollModalId] = useState<number | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);

  const hasProcessedNavigationStateRef = useRef(false);

  // Fetch user profile and onboarding status on mount
  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        setUserName(user?.name || null);
      })
      .catch((error) => {
        console.error("Failed to load user profile:", error);
        setUserName(null);
      });

    // Check onboarding status from localStorage (synchronous)
    try {
      const status = getOnboardingStatus();
      console.log("[FeedPage] Onboarding status:", status);
      setOnboardingStatus(status);
      if (status.first_run) {
        console.log("[FeedPage] Showing onboarding (first_run=true)");
        setShowOnboarding(true);
      } else {
        console.log("[FeedPage] Not showing onboarding (first_run=false)");
        setShowOnboarding(false);
      }
    } catch (error) {
      console.error("Failed to load onboarding status:", error);
      // Default to showing onboarding if we can't determine status
      setShowOnboarding(true);
    }
  }, []);

  // Load initial feed data
  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activityType = activeFilter === "all" ? undefined : activeFilter;
      const data = await getActivityFeed(INITIAL_LIMIT, 0, activityType);
      // #region agent log
      if (data.length > 0) {
        const sampleItem = data[0];
        fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location: 'FeedPage.tsx:166', message: 'loadInitialData: sample item reactions', data: { activityId: sampleItem.id, reactions: sampleItem.reactions, userReaction: sampleItem.user_reaction }, timestamp: Date.now(), sessionId: 'debug-session', runId: 'run1', hypothesisId: 'B' }) }).catch(() => { });
      }
      // #endregion
      setFeedItems(data);
      setOffset(data.length);
      setHasMore(data.length >= INITIAL_LIMIT);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon activiteit niet laden";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }, [activeFilter]);

  // Load more feed data
  const handleLoadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);
    try {
      const activityType = activeFilter === "all" ? undefined : activeFilter;
      const data = await getActivityFeed(LOAD_MORE_LIMIT, offset, activityType);
      if (data.length > 0) {
        setFeedItems((prev) => [...prev, ...data]);
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
  }, [isLoadingMore, hasMore, offset, activeFilter]);

  // Check for filter in navigation state on mount (only once per navigation)
  useEffect(() => {
    const stateFilter = (location.state as { filter?: ActivityFilter })?.filter;
    if (stateFilter && stateFilter !== activeFilter && !hasProcessedNavigationStateRef.current) {
      hasProcessedNavigationStateRef.current = true;
      setActiveFilter(stateFilter);
      // Clear navigation state to avoid re-applying on re-render
      window.history.replaceState({}, "", location.pathname);
    }
  }, [location.state, activeFilter, location.pathname]);

  // Reset the ref when location changes (new navigation)
  useEffect(() => {
    hasProcessedNavigationStateRef.current = false;
  }, [location.pathname]);

  // Reload when filter changes
  useEffect(() => {
    setFeedItems([]);
    setOffset(0);
    setHasMore(true);
    loadInitialData();
  }, [loadInitialData]);

  // Handle reaction toggle
  const handleReactionToggle = useCallback(async (activityId: number, reactionType: ReactionType) => {
    try {
      // Call toggle API
      const result = await toggleActivityReaction(activityId, reactionType);

      // Fetch updated reactions from server to get accurate counts
      const reactionsData = await getActivityReactions(activityId);

      // Update state with server response
      setFeedItems((prev) =>
        prev.map((item) => {
          if (item.id !== activityId) return item;

          return {
            ...item,
            reactions: reactionsData.reactions || {},
            user_reaction: result.is_active ? reactionType : null,
          };
        })
      );
    } catch (error) {
      toast.error("Kon reactie niet toevoegen");
      // Optionally reload the feed item to get accurate state
      // This could be done by refreshing just this item from the API
    }
  }, []);

  // Handle bookmark toggle
  const handleBookmark = useCallback(async (activityId: number) => {
    try {
      const result = await toggleActivityBookmark(activityId);
      // Optimistic update
      setFeedItems((prev) =>
        prev.map((item) =>
          item.id === activityId ? { ...item, is_bookmarked: result.bookmarked } : item
        )
      );
    } catch (error) {
      toast.error("Kon bookmark niet toevoegen");
      // Reload to get correct state
      loadInitialData();
    }
  }, [loadInitialData]);

  // Handle card click navigation
  const handleCardClick = useCallback((item: ActivityItem) => {
    if (item.activity_type === "bulletin_post") {
      navigate(`/#/feed?tab=bulletin&post=${item.payload?.bulletin_post_id || ""}`);
    } else if (item.activity_type === "note" && item.location_id) {
      // Navigate to location detail for notes (note_id can be added later if needed)
      navigate(`/#/locations/${item.location_id}`);
    } else if (item.location_id) {
      navigate(`/#/locations/${item.location_id}`);
    }
  }, [navigate]);

  // Handle image click
  const handleImageClick = useCallback((imageUrl: string) => {
    setImageModalUrl(imageUrl);
    setImageModalOpen(true);
  }, []);

  // Handle location click
  const handleLocationClick = useCallback((locationId: number) => {
    navigate(`/#/locations/${locationId}`);
  }, [navigate]);

  // Handle poll click
  const handlePollClick = useCallback((pollId: number) => {
    setPollModalId(pollId);
    setPollModalOpen(true);
  }, []);

  // Transform feed items to FeedCard props
  const feedCardProps = useMemo(() => {
    return feedItems.map((item) =>
      transformActivityItem(item, handleReactionToggle, handleBookmark, handleCardClick, handleImageClick, handleLocationClick, handlePollClick)
    );
  }, [feedItems, handleReactionToggle, handleBookmark, handleCardClick, handleImageClick, handleLocationClick, handlePollClick]);

  // Handle notification click (placeholder)
  const handleNotificationClick = useCallback(() => {
    // TODO: Implement notification navigation
    console.log("Notification clicked");
  }, []);

  // Show onboarding if first_run is true
  if (showOnboarding && onboardingStatus?.first_run) {
    return (
      <OnboardingFlow
        onComplete={() => {
          setShowOnboarding(false);
          // Reload feed data
          loadInitialData();
        }}
      />
    );
  }

  return (
    <AppViewportShell variant="content">
      <div className="flex flex-col h-full relative">
        {/* Red gradient overlay */}
        <div
          className="absolute inset-x-0 top-0 pointer-events-none z-0"
          style={{
            height: '25%',
            background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
          }}
        />
        <AppHeader onNotificationClick={handleNotificationClick} />
        <div className="flex-1 overflow-y-auto px-4 pb-24 relative z-10">
          <GreetingBlock userName={userName} />
          <FeedFilterTabs activeFilter={activeFilter} onFilterChange={setActiveFilter} />
          {activeFilter === "all" ? (
            <DashboardOverview className="mt-2" />
          ) : error ? (
            <div className="mt-4 rounded-xl border border-border/80 bg-card p-5 text-center shadow-soft">
              <p className="text-foreground">{error}</p>
            </div>
          ) : (
            <FeedList
              items={feedCardProps}
              isLoading={isLoading}
              isLoadingMore={isLoadingMore}
              hasMore={hasMore}
              onLoadMore={handleLoadMore}
              emptyMessage="Er is nog geen activiteit. Begin met check-ins, reacties of notities!"
              className="mt-2"
            />
          )}
        </div>
        <FooterTabs />
      </div>
      <ImageModal
        imageUrl={imageModalUrl}
        open={imageModalOpen}
        onOpenChange={setImageModalOpen}
      />
      <PollModal
        pollId={pollModalId}
        open={pollModalOpen}
        onOpenChange={setPollModalOpen}
      />
    </AppViewportShell>
  );
}

// Frontend/src/pages/FeedPage.tsx
import { AppHeader } from "@/components/feed/AppHeader";
import { DashboardOverview } from "@/components/feed/DashboardOverview";
import type { FeedCardProps } from "@/components/feed/FeedCard";
import { FeedFilterTabs, type ActivityFilter } from "@/components/feed/FeedFilterTabs";
import { FeedList } from "@/components/feed/FeedList";
import { GreetingBlock } from "@/components/feed/GreetingBlock";
import { ImageModal } from "@/components/feed/ImageModal";
import { PollFeed } from "@/components/feed/PollFeed";
import { PollModal } from "@/components/feed/PollModal";
import { FooterTabs } from "@/components/FooterTabs";
import { AppViewportShell } from "@/components/layout";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { getActivityFeed, getActivityReactions, getCurrentUser, getOnboardingStatus, getOneCikanlar, getWeekFeedback, toggleActivityBookmark, toggleActivityReaction, type ActivityItem, type OnboardingStatus, type ReactionType } from "@/lib/api";
import { WeekFeedbackCard } from "@/components/feed/WeekFeedbackCard";
import { PeriodTabs, type PeriodFilter } from "@/components/onecikanlar/PeriodTabs";
import { LeaderboardCards } from "@/components/onecikanlar/LeaderboardCards";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useMascotteFeedback } from "@/hooks/useMascotteFeedback";
import { useUserAuth } from "@/hooks/useUserAuth";

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
  onImageClick?: (imageUrl: string) => void,
  onLocationClick?: (locationId: number) => void,
  onPollClick?: (pollId: number) => void,
  onUserClick?: (userId: string) => void
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
      name: item.user?.name || "Anonieme gebruiker",
      primary_role: item.user?.primary_role || null,
      secondary_role: item.user?.secondary_role || null,
      id: item.user?.id || null,
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
    labels: item.labels || null,
    onReactionToggle: (reactionType: ReactionType) => onReactionToggle(item.id, reactionType),
    onBookmark: () => onBookmark(item.id),
    onImageClick,
    onLocationClick,
    onPollClick,
    onUserClick: item.user?.id && onUserClick ? () => onUserClick(item.user!.id!) : undefined,
  };

  return transformed;
}

export default function FeedPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { showMascotteFeedback } = useMascotteFeedback();
  const { isAuthenticated } = useUserAuth();

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
  const [weekFeedback, setWeekFeedback] = useState<{
    should_show: boolean;
    message: string;
    week_start: string;
  } | null>(null);
  const [weekFeedbackDismissed, setWeekFeedbackDismissed] = useState(false);
  
  // Öne Çıkanlar state
  const [period, setPeriod] = useState<PeriodFilter>("week");
  const [cityKey, setCityKey] = useState<string | null>(null);
  const [leaderboardData, setLeaderboardData] = useState<Awaited<ReturnType<typeof getOneCikanlar>> | null>(null);
  const [leaderboardLoading, setLeaderboardLoading] = useState<boolean>(false);
  const [leaderboardError, setLeaderboardError] = useState<string | null>(null);

  const hasProcessedNavigationStateRef = useRef(false);

  // Fetch user profile, onboarding status, and week feedback on mount
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

    // Fetch week feedback
    getWeekFeedback()
      .then((feedback) => {
        // Check localStorage to see if user has already seen feedback this week
        const storageKey = `week_feedback_${feedback.week_start}`;
        const hasSeen = localStorage.getItem(storageKey) === "true";
        
        if (feedback.should_show && !hasSeen) {
          setWeekFeedback(feedback);
        } else {
          setWeekFeedbackDismissed(true);
        }
      })
      .catch((error) => {
        console.error("Failed to load week feedback:", error);
        // Silently fail - week feedback is optional
      });
  }, []);

  // Load initial feed data
  const loadInitialData = useCallback(async () => {
    // Don't load if user is not authenticated
    if (!isAuthenticated) {
      setFeedItems([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      // Don't pass "one_cikanlar" or "all" as activityType
      const activityType = activeFilter === "all" || activeFilter === "one_cikanlar" 
        ? undefined 
        : activeFilter;
      const data = await getActivityFeed(INITIAL_LIMIT, 0, activityType);
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
  }, [activeFilter, isAuthenticated]);

  // Load more feed data
  const handleLoadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);
    try {
      // Don't pass "one_cikanlar" or "all" as activityType
      const activityType = activeFilter === "all" || activeFilter === "one_cikanlar"
        ? undefined
        : activeFilter;
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

  // Clear feed items when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      setFeedItems([]);
      setOffset(0);
      setHasMore(true);
    }
  }, [isAuthenticated]);

  // Reload when filter changes
  useEffect(() => {
    // Only load activity feed if not showing Öne Çıkanlar and user is authenticated
    if (activeFilter !== "one_cikanlar" && isAuthenticated) {
      setFeedItems([]);
      setOffset(0);
      setHasMore(true);
      loadInitialData();
    }
  }, [loadInitialData, activeFilter, isAuthenticated]);

  // Fetch leaderboard data when Öne Çıkanlar is active
  useEffect(() => {
    if (activeFilter !== "one_cikanlar") {
      // Reset leaderboard state when switching away
      setLeaderboardData(null);
      setLeaderboardError(null);
      return;
    }

    const fetchLeaderboardData = async () => {
      setLeaderboardLoading(true);
      setLeaderboardError(null);
      try {
        // Convert period filter to API period
        const apiPeriod = period === "city" ? "week" : period; // Default to week for city filter
        const result = await getOneCikanlar(apiPeriod, period === "city" ? cityKey : null);
        setLeaderboardData(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Kon leaderboard niet laden";
        setLeaderboardError(message);
        toast.error(message);
      } finally {
        setLeaderboardLoading(false);
      }
    };

    fetchLeaderboardData();
  }, [activeFilter, period, cityKey]);

  // Show mascotte feedback when week feedback card appears
  useEffect(() => {
    if (weekFeedback && !weekFeedbackDismissed) {
      showMascotteFeedback("week_active");
    }
  }, [weekFeedback, weekFeedbackDismissed, showMascotteFeedback]);

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


  // Handle image click
  const handleImageClick = useCallback((imageUrl: string) => {
    setImageModalUrl(imageUrl);
    setImageModalOpen(true);
  }, []);

  // Handle location click
  const handleLocationClick = useCallback((locationId: number) => {
    navigate(`/locations/${locationId}`);
  }, [navigate]);

  // Handle poll click
  const handlePollClick = useCallback((pollId: number) => {
    setPollModalId(pollId);
    setPollModalOpen(true);
  }, []);

  // Handle period change for Öne Çıkanlar
  const handlePeriodChange = useCallback((newPeriod: PeriodFilter) => {
    setPeriod(newPeriod);
    // Reset cityKey when switching away from city filter
    if (newPeriod !== "city") {
      setCityKey(null);
    }
  }, []);

  // Handle user click
  const handleUserClick = useCallback((userId: string) => {
    // Navigate to account page (or future user profile page)
    navigate("/account");
  }, [navigate]);

  // Transform feed items to FeedCard props
  const feedCardProps = useMemo(() => {
    return feedItems.map((item) =>
      transformActivityItem(item, handleReactionToggle, handleBookmark, handleImageClick, handleLocationClick, handlePollClick, handleUserClick)
    );
  }, [feedItems, handleReactionToggle, handleBookmark, handleImageClick, handleLocationClick, handlePollClick, handleUserClick]);

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
          {activeFilter === "one_cikanlar" && (
            <PeriodTabs 
              activePeriod={period} 
              onPeriodChange={handlePeriodChange} 
              className="mt-2" 
            />
          )}
          {weekFeedback && !weekFeedbackDismissed && activeFilter !== "one_cikanlar" && (
            <WeekFeedbackCard
              message={weekFeedback.message}
              onDismiss={() => {
                // Save to localStorage that user has seen feedback this week
                const storageKey = `week_feedback_${weekFeedback.week_start}`;
                localStorage.setItem(storageKey, "true");
                setWeekFeedbackDismissed(true);
              }}
              className="mt-2"
            />
          )}
          {activeFilter === "one_cikanlar" ? (
            <>
              {leaderboardLoading && (
                <div className="mt-4 text-center py-8 text-muted-foreground">Laden...</div>
              )}
              {leaderboardError && (
                <div className="mt-4 rounded-xl border border-border/80 bg-card p-5 text-center shadow-soft">
                  <p className="text-foreground">{leaderboardError}</p>
                </div>
              )}
              {!leaderboardLoading && !leaderboardError && leaderboardData && (
                <LeaderboardCards
                  cards={leaderboardData.cards}
                  onUserClick={handleUserClick}
                  className="mt-2"
                />
              )}
            </>
          ) : activeFilter === "all" ? (
            <DashboardOverview className="mt-2" />
          ) : activeFilter === "poll_response" ? (
            <PollFeed className="mt-2" />
          ) : !isAuthenticated ? (
            <FeedList
              items={[]}
              isLoading={false}
              isLoadingMore={false}
              hasMore={false}
              emptyMessage="Er is nog geen activiteit. Begin met check-ins, reacties of notities!"
              className="mt-2"
              showLoginPrompt={true}
              loginMessage={
                activeFilter === "check_in"
                  ? "Log in om je check-ins te zien"
                  : activeFilter === "note"
                  ? "Log in om je notities te zien"
                  : "Log in om je activiteit te zien"
              }
            />
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
              showLoginPrompt={false}
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

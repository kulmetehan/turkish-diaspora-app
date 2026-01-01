// Frontend/src/pages/FeedPage.tsx
import { AppHeader } from "@/components/feed/AppHeader";
import { DashboardOverview } from "@/components/feed/DashboardOverview";
import type { FeedCardProps } from "@/components/feed/FeedCard";
import { FeedFilterTabs, type ActivityFilter } from "@/components/feed/FeedFilterTabs";
import { FeedList } from "@/components/feed/FeedList";
import { GreetingBlock } from "@/components/feed/GreetingBlock";
import { ImageModal } from "@/components/feed/ImageModal";
import { TimelineFeed } from "@/components/timeline/TimelineFeed";
import { FooterTabs } from "@/components/FooterTabs";
import { AppViewportShell } from "@/components/layout";
import { getActivityFeed, getActivityReactions, getCurrentUser, getOneCikanlar, getWeekFeedback, toggleActivityBookmark, toggleActivityReaction, type ActivityItem, type ReactionType } from "@/lib/api";
import { WeekFeedbackCard } from "@/components/feed/WeekFeedbackCard";
import { PeriodTabs, type PeriodFilter } from "@/components/onecikanlar/PeriodTabs";
import { LeaderboardCards } from "@/components/onecikanlar/LeaderboardCards";
import { FavoriteTabs, type FavoriteFilter } from "@/components/favorites/FavoriteTabs";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useMascotteFeedback } from "@/hooks/useMascotteFeedback";
import { useTranslation } from "@/hooks/useTranslation";
import { useUserAuth } from "@/hooks/useUserAuth";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

// Helper function to get activity message (reused from ActivityCard logic)
function getActivityMessage(item: ActivityItem, t: (key: string, params?: Record<string, string>) => string): string {
  const locationName = item.location_name || "een locatie";

  switch (item.activity_type) {
    case "check_in":
      return t("feed.card.activity.checkIn").replace("{location}", locationName);
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
      return t("feed.card.activity.reaction")
        .replace("{emoji}", emoji)
        .replace("{location}", locationName);
    case "note":
      return t("feed.card.activity.note").replace("{location}", locationName);
    case "poll_response":
      return t("feed.card.activity.pollResponse");
    case "favorite":
      return t("feed.card.activity.favorite").replace("{location}", locationName);
    case "event":
      return t("feed.card.activity.event").replace("{location}", locationName);
    default:
      return t("feed.card.activity.default").replace("{location}", locationName);
  }
}

// Transform ActivityItem to FeedCardProps
function transformActivityItem(
  item: ActivityItem,
  onReactionToggle: (id: number, reactionType: ReactionType) => void,
  onBookmark: (id: number) => void,
  t: (key: string, params?: Record<string, string>) => string,
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
      name: item.user?.name || null,
      primary_role: item.user?.primary_role || null,
      secondary_role: item.user?.secondary_role || null,
      id: item.user?.id || null,
    },
    locationName: item.location_name || null,
    locationId: item.location_id || null,
    timestamp: item.created_at,
    contentText: getActivityMessage(item, t),
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
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { showMascotteFeedback } = useMascotteFeedback();
  const { isAuthenticated } = useUserAuth();
  const seo = useSeo();

  // State management
  // Read filter from hash params (for email links) or navigation state
  const getFilterFromHash = (): ActivityFilter | null => {
    if (typeof window === "undefined") return null;
    const hash = window.location.hash ?? "";
    const queryIndex = hash.indexOf("?");
    if (queryIndex < 0) return null;
    const query = hash.slice(queryIndex + 1);
    const params = new URLSearchParams(query);
    const filter = params.get("filter");
    if (filter && ["all", "one_cikanlar", "check_in", "note", "poll_response", "favorite", "timeline", "prikbord"].includes(filter)) {
      // Support both old "prikbord" and new "timeline" for backwards compatibility
      return (filter === "prikbord" ? "timeline" : filter) as ActivityFilter;
    }
    return null;
  };
  const hashFilter = getFilterFromHash();
  const stateFilter = (location.state as { filter?: ActivityFilter })?.filter;
  const initialFilter = hashFilter || stateFilter || "all";
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
  
  // Favorieten state
  const [favoriteFilter, setFavoriteFilter] = useState<FavoriteFilter>("mijn");
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const hasProcessedNavigationStateRef = useRef(false);

  // Fetch user profile and week feedback on mount
  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        setUserName(user?.name || null);
        setCurrentUserId(user?.id || null);
      })
      .catch((error) => {
        console.error("Failed to load user profile:", error);
        setUserName(null);
        setCurrentUserId(null);
      });

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
      // Don't pass "one_cikanlar", "all", "timeline", or "prikbord" as activityType
      // These have their own components
      const activityType = activeFilter === "all" || activeFilter === "one_cikanlar" || activeFilter === "timeline" || activeFilter === "prikbord"
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
      // Don't pass "one_cikanlar", "all", "timeline", or "prikbord" as activityType
      // These have their own components
      const activityType = activeFilter === "all" || activeFilter === "one_cikanlar" || activeFilter === "timeline" || activeFilter === "prikbord"
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
    // Only load activity feed if not showing Öne Çıkanlar, Timeline, or Prikbord and user is authenticated
    if (activeFilter !== "one_cikanlar" && activeFilter !== "timeline" && activeFilter !== "prikbord" && isAuthenticated) {
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

  // Reset favorite filter when switching away from favorites tab
  useEffect(() => {
    if (activeFilter !== "favorite") {
      setFavoriteFilter("mijn");
    }
  }, [activeFilter]);

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
      toast.error(t("feed.toast.reactionError"));
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
      toast.error(t("feed.toast.bookmarkAddError"));
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

  // Handle poll click (no longer needed, polls are inline)
  const handlePollClick = useCallback((pollId: number) => {
    // Polls are now inline, no modal needed
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
    let transformed = feedItems.map((item) =>
      transformActivityItem(item, handleReactionToggle, handleBookmark, t, handleImageClick, handleLocationClick, handlePollClick, handleUserClick)
    );

    // Apply favorite filter if activeFilter is "favorite"
    if (activeFilter === "favorite") {
      // Filter out anonymous users (no user.id)
      transformed = transformed.filter((item) => item.user.id !== null);

      // Apply favorite filter (mijn vs anderen)
      if (favoriteFilter === "mijn") {
        // Only show favorites from current user
        transformed = transformed.filter((item) => item.user.id === currentUserId);
      } else {
        // Show favorites from others (already filtered out anonymous users above)
        transformed = transformed.filter((item) => item.user.id !== currentUserId);
      }
    }

    return transformed;
  }, [feedItems, handleReactionToggle, handleBookmark, handleImageClick, handleLocationClick, handlePollClick, handleUserClick, activeFilter, favoriteFilter, currentUserId]);

  // Handle notification click (placeholder)
  const handleNotificationClick = useCallback(() => {
    // TODO: Implement notification navigation
    console.log("Notification clicked");
  }, []);

  return (
    <>
      <SeoHead {...seo} />
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
          {activeFilter === "favorite" && (
            <FavoriteTabs 
              activeFilter={favoriteFilter} 
              onFilterChange={setFavoriteFilter} 
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
          {activeFilter === "one_cikanlar" && !isAuthenticated ? (
            <FeedList
              items={[]}
              isLoading={false}
              isLoadingMore={false}
              hasMore={false}
              emptyMessage=""
              className="mt-2"
              showLoginPrompt={true}
              loginMessage="Log in om Öne Çıkanlar te zien"
            />
          ) : activeFilter === "one_cikanlar" ? (
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
          ) : activeFilter === "favorite" ? (
            !isAuthenticated ? (
              <FeedList
                items={[]}
                isLoading={false}
                isLoadingMore={false}
                hasMore={false}
                emptyMessage=""
                className="mt-2"
                showLoginPrompt={true}
                loginMessage="Log in om favorieten te zien"
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
                emptyMessage={
                  favoriteFilter === "mijn"
                    ? "Je hebt nog geen favorieten toegevoegd. Voeg locaties toe aan je favorieten!"
                    : "Er zijn nog geen favorieten van anderen."
                }
                className="mt-2"
                showLoginPrompt={false}
              />
            )
          ) : activeFilter === "all" ? (
            <DashboardOverview className="mt-2" />
          ) : activeFilter === "timeline" || activeFilter === "prikbord" ? (
            <TimelineFeed className="mt-2" />
          ) : !isAuthenticated ? (
            <FeedList
              items={[]}
              isLoading={false}
              isLoadingMore={false}
              hasMore={false}
              emptyMessage="Er is nog geen activiteit. Begin met check-ins, reacties of notities!"
              className="mt-2"
              showLoginPrompt={true}
              loginMessage="Log in om je activiteit te zien"
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
    </AppViewportShell>
    </>
  );
}

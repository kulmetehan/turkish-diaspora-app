// Frontend/src/components/timeline/TimelineFeed.tsx
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/ui/cn";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { PrikbordComposer } from "@/components/prikbord/PrikbordComposer";
import { TimelineSubFilters, type TimelineSubFilter } from "./TimelineSubFilters";
import { SharedLinkCard } from "@/components/prikbord/SharedLinkCard";
import { FeedCard, type FeedCardProps } from "@/components/feed/FeedCard";
import { PollCard } from "@/components/polls/PollCard";
import { getSharedLinks } from "@/lib/api/prikbord";
import { getActivityFeed, toggleActivityReaction, toggleActivityBookmark, type ActivityItem, type ReactionType } from "@/lib/api";
import { listPolls, getPollStats, submitPollResponse, type Poll, type PollStats } from "@/lib/api";
import { toggleSharedLinkReaction, deleteSharedLink, type SharedLink } from "@/lib/api/prikbord";
import { useTranslation } from "@/hooks/useTranslation";
import { useNavigate } from "react-router-dom";

interface TimelineFeedProps {
  className?: string;
}

const INITIAL_LIMIT = 20;
const LOAD_MORE_LIMIT = 20;

type TimelineItem =
  | { type: "prikbord"; data: SharedLink; timestamp: string }
  | { type: "activity"; data: ActivityItem; timestamp: string }
  | { type: "poll"; data: Poll; timestamp: string };

// Helper function to get activity message
function getActivityMessage(item: ActivityItem, t: (key: string, params?: Record<string, string>) => string): string | null {
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
    case "bulletin_post":
      const title = (item.payload?.title as string) || "";
      return t("feed.card.activity.bulletinPost").replace("{title}", title);
    case "event":
      return t("feed.card.activity.event").replace("{location}", locationName);
    default:
      // Return null for unknown activity types - will be filtered out
      console.warn("getActivityMessage: Unknown activity type", item.activity_type);
      return null;
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
  onUserClick?: (userId: string) => void
): FeedCardProps | null {
  // Don't transform items without user or with null message
  const activityMessage = getActivityMessage(item, t);
  if (!item.user || !activityMessage) {
    return null;
  }

  const noteContent = item.activity_type === "note"
    ? (item.payload?.note_preview as string) || (item.payload?.content as string) || null
    : null;

  return {
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
    categoryKey: item.category_key || null,
    timestamp: item.created_at,
    contentText: activityMessage,
    noteContent,
    pollId: null,
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
    onPollClick: undefined,
    onUserClick: item.user?.id && onUserClick ? () => onUserClick(item.user!.id!) : undefined,
  };
}

export function TimelineFeed({ className }: TimelineFeedProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [subFilter, setSubFilter] = useState<TimelineSubFilter>("all");
  
  // Data state
  const [prikbordLinks, setPrikbordLinks] = useState<SharedLink[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [polls, setPolls] = useState<Poll[]>([]);
  
  // Loading state
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination state
  const [prikbordOffset, setPrikbordOffset] = useState(0);
  const [activityOffset, setActivityOffset] = useState(0);
  const [pollOffset, setPollOffset] = useState(0);
  const [hasMorePrikbord, setHasMorePrikbord] = useState(true);
  const [hasMoreActivity, setHasMoreActivity] = useState(true);
  const [hasMorePolls, setHasMorePolls] = useState(true);
  
  // Poll state
  const [pollStats, setPollStats] = useState<Record<number, PollStats>>({});
  const [selectedOptions, setSelectedOptions] = useState<Record<number, number>>({});
  const [submittingPolls, setSubmittingPolls] = useState<Set<number>>(new Set());
  const [respondedPolls, setRespondedPolls] = useState<Set<number>>(new Set());
  
  const isLoadingRef = useRef(false);

  // Load initial data
  const loadInitialData = useCallback(async () => {
    if (isLoadingRef.current) return;
    isLoadingRef.current = true;
    setIsLoading(true);
    setError(null);
    
    try {
      // Load all three types in parallel
      const [linksData, activityData, pollsData] = await Promise.all([
        getSharedLinks({}, INITIAL_LIMIT, 0),
        getActivityFeed(INITIAL_LIMIT, 0, undefined),
        listPolls(undefined, INITIAL_LIMIT),
      ]);
      
      setPrikbordLinks(linksData);
      setActivities(activityData);
      setPolls(pollsData);
      
      setPrikbordOffset(linksData.length);
      setActivityOffset(activityData.length);
      setPollOffset(pollsData.length);
      
      setHasMorePrikbord(linksData.length >= INITIAL_LIMIT);
      setHasMoreActivity(activityData.length >= INITIAL_LIMIT);
      setHasMorePolls(pollsData.length >= INITIAL_LIMIT);
      
      // Track responded polls
      const respondedSet = new Set<number>();
      pollsData.forEach(poll => {
        if (poll.user_has_responded) {
          respondedSet.add(poll.id);
        }
      });
      setRespondedPolls(respondedSet);
      
      // Fetch stats for responded polls
      const respondedPollsList = pollsData.filter(p => p.user_has_responded);
      const statsPromises = respondedPollsList.map(async (poll) => {
        try {
          const stats = await getPollStats(poll.id);
          return { pollId: poll.id, stats };
        } catch {
          return { pollId: poll.id, stats: null };
        }
      });
      const statsResults = await Promise.all(statsPromises);
      const statsMap: Record<number, PollStats> = {};
      statsResults.forEach(({ pollId, stats }) => {
        if (stats) {
          statsMap[pollId] = stats;
        }
      });
      setPollStats(statsMap);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon timeline niet laden";
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
      isLoadingRef.current = false;
    }
  }, []);

  // Load more data
  const loadMore = useCallback(async () => {
    if (isLoadingMore || (!hasMorePrikbord && !hasMoreActivity && !hasMorePolls)) return;
    
    setIsLoadingMore(true);
    try {
      const promises: Promise<any>[] = [];
      
      if (hasMorePrikbord) {
        promises.push(getSharedLinks({}, LOAD_MORE_LIMIT, prikbordOffset).then(data => {
          if (data.length > 0) {
            setPrikbordLinks(prev => [...prev, ...data]);
            setPrikbordOffset(prev => prev + data.length);
            setHasMorePrikbord(data.length >= LOAD_MORE_LIMIT);
          } else {
            setHasMorePrikbord(false);
          }
        }));
      }
      
      if (hasMoreActivity) {
        promises.push(getActivityFeed(LOAD_MORE_LIMIT, activityOffset, undefined).then(data => {
          if (data.length > 0) {
            setActivities(prev => [...prev, ...data]);
            setActivityOffset(prev => prev + data.length);
            setHasMoreActivity(data.length >= LOAD_MORE_LIMIT);
          } else {
            setHasMoreActivity(false);
          }
        }));
      }
      
      if (hasMorePolls) {
        promises.push(listPolls(undefined, LOAD_MORE_LIMIT).then(data => {
          // Filter out polls we already have
          setPolls(prev => {
            const existingIds = new Set(prev.map(p => p.id));
            const newPolls = data.filter(p => !existingIds.has(p.id));
            if (newPolls.length > 0) {
              setPollOffset(prev => prev + newPolls.length);
              setHasMorePolls(newPolls.length >= LOAD_MORE_LIMIT);
              return [...prev, ...newPolls];
            } else {
              setHasMorePolls(false);
              return prev;
            }
          });
        }));
      }
      
      await Promise.all(promises);
    } catch (err) {
      toast.error("Kon meer content niet laden");
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMorePrikbord, hasMoreActivity, hasMorePolls, prikbordOffset, activityOffset]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // When filter changes to "notes" or "check_ins", ensure we have at least 3 items
  useEffect(() => {
    if ((subFilter === "notes" || subFilter === "check_ins") && !isLoading && !isLoadingMore) {
      // Count items of the requested type
      const count = subFilter === "notes" 
        ? activities.filter(a => a.activity_type === "note").length
        : activities.filter(a => a.activity_type === "check_in").length;
      
      // If we have less than 3 items and there's more to load, load more
      if (count < 3 && hasMoreActivity) {
        loadMore();
      }
    }
  }, [subFilter, activities, isLoading, isLoadingMore, hasMoreActivity, loadMore]);

  // Combine and sort timeline items
  const timelineItems = useMemo(() => {
    const items: TimelineItem[] = [];
    
    // Add prikbord links (only if sub-filter is "all")
    if (subFilter === "all") {
      prikbordLinks.forEach(link => {
        items.push({ type: "prikbord", data: link, timestamp: link.created_at });
      });
    }
    
    // Add activities (filtered by sub-filter and user presence)
    activities
      .filter(activity => activity.user !== null && activity.user !== undefined)
      .forEach(activity => {
        if (subFilter === "all") {
          // Show all activities when filter is "all"
          items.push({ type: "activity", data: activity, timestamp: activity.created_at });
        } else if (subFilter === "check_ins" && activity.activity_type === "check_in") {
          items.push({ type: "activity", data: activity, timestamp: activity.created_at });
        } else if (subFilter === "notes" && activity.activity_type === "note") {
          items.push({ type: "activity", data: activity, timestamp: activity.created_at });
        }
      });
    
    // Add polls (if sub-filter allows)
    if (subFilter === "all" || subFilter === "polls") {
      polls.forEach(poll => {
        items.push({ type: "poll", data: poll, timestamp: poll.starts_at });
      });
    }
    
    // Sort by timestamp (newest first)
    return items.sort((a, b) => {
      const dateA = new Date(a.timestamp).getTime();
      const dateB = new Date(b.timestamp).getTime();
      return dateB - dateA;
    });
  }, [prikbordLinks, activities, polls, subFilter]);

  // Handle post success
  const handlePostSuccess = useCallback((newPost?: SharedLink) => {
    if (newPost) {
      setPrikbordLinks(prev => [newPost, ...prev]);
      setPrikbordOffset(prev => prev + 1);
    } else {
      loadInitialData();
    }
  }, [loadInitialData]);

  // Handle reaction toggle for activities
  const handleActivityReactionToggle = useCallback(async (activityId: number, reactionType: ReactionType) => {
    try {
      await toggleActivityReaction(activityId, reactionType);
      setActivities(prev =>
        prev.map(item => {
          if (item.id === activityId) {
            // Optimistic update - actual data will be refreshed on next load
            return { ...item, is_liked: !item.is_liked };
          }
          return item;
        })
      );
    } catch (err) {
      toast.error(t("feed.toast.reactionError"));
    }
  }, [t]);

  // Handle bookmark toggle for activities
  const handleActivityBookmark = useCallback(async (activityId: number) => {
    try {
      await toggleActivityBookmark(activityId);
      setActivities(prev =>
        prev.map(item => {
          if (item.id === activityId) {
            return { ...item, is_bookmarked: !item.is_bookmarked };
          }
          return item;
        })
      );
    } catch (err) {
      toast.error(t("feed.toast.bookmarkAddError"));
    }
  }, [t]);

  // Handle reaction toggle for prikbord links
  const handlePrikbordReactionToggle = useCallback(async (linkId: number, reactionType: ReactionType) => {
    try {
      const result = await toggleSharedLinkReaction(linkId, reactionType);
      setPrikbordLinks(prev =>
        prev.map(link => {
          if (link.id === linkId) {
            const currentReactions = link.reactions || {};
            const newReactions = { ...currentReactions };
            
            if (result.is_active) {
              newReactions[reactionType] = result.count;
              return {
                ...link,
                reactions: newReactions,
                user_reaction: reactionType,
              };
            } else {
              if (newReactions[reactionType]) {
                newReactions[reactionType] = result.count;
                if (newReactions[reactionType] === 0) {
                  delete newReactions[reactionType];
                }
              }
              return {
                ...link,
                reactions: Object.keys(newReactions).length > 0 ? newReactions : null,
                user_reaction: link.user_reaction === reactionType ? null : link.user_reaction,
              };
            }
          }
          return link;
        })
      );
    } catch (err: any) {
      toast.error("Kon reactie niet updaten", {
        description: err.message || "Er is een fout opgetreden",
      });
    }
  }, []);

  // Handle delete for prikbord links
  const handlePrikbordDelete = useCallback(async (linkId: number) => {
    try {
      setPrikbordLinks(prev => prev.filter(link => link.id !== linkId));
      setPrikbordOffset(prev => Math.max(0, prev - 1));
      await deleteSharedLink(linkId);
      toast.success("Post verwijderd");
    } catch (err: any) {
      toast.error("Kon post niet verwijderen", {
        description: err.message || "Er is een fout opgetreden",
      });
      loadInitialData();
    }
  }, [loadInitialData]);

  // Handle poll option select
  const handlePollOptionSelect = useCallback((pollId: number, optionId: number) => {
    if (respondedPolls.has(pollId) || submittingPolls.has(pollId)) return;
    setSelectedOptions(prev => ({ ...prev, [pollId]: optionId }));
  }, [respondedPolls, submittingPolls]);

  // Handle poll vote submit
  const handlePollSubmitVote = useCallback(async (pollId: number) => {
    const optionId = selectedOptions[pollId];
    if (!optionId || respondedPolls.has(pollId) || submittingPolls.has(pollId)) return;

    try {
      setSubmittingPolls(prev => new Set(prev).add(pollId));
      await submitPollResponse(pollId, optionId);
      
      setRespondedPolls(prev => new Set(prev).add(pollId));
      toast.success("Diaspora Nabzı'na katkı sağladın", { duration: 3000 });

      // Fetch stats
      try {
        const stats = await getPollStats(pollId);
        setPollStats(prev => ({ ...prev, [pollId]: stats }));
      } catch (err) {
        console.error("Failed to load poll stats:", err);
      }

      setPolls(prev => prev.map(poll => 
        poll.id === pollId ? { ...poll, user_has_responded: true } : poll
      ));

      setSelectedOptions(prev => {
        const next = { ...prev };
        delete next[pollId];
        return next;
      });
    } catch (err: any) {
      const errorMessage = err.message || "";
      const isAlreadyResponded = 
        err.status === 409 || 
        errorMessage.includes("409") ||
        errorMessage.includes("Already responded") || 
        errorMessage.includes("already");
      
      if (isAlreadyResponded) {
        setRespondedPolls(prev => new Set(prev).add(pollId));
        loadInitialData();
        return;
      }
      toast.error("Kon niet stemmen");
    } finally {
      setSubmittingPolls(prev => {
        const next = new Set(prev);
        next.delete(pollId);
        return next;
      });
    }
  }, [selectedOptions, respondedPolls, submittingPolls, loadInitialData]);

  // Handle image click
  const handleImageClick = useCallback((imageUrl: string) => {
    // Could open image modal here if needed
  }, []);

  // Handle location click
  const handleLocationClick = useCallback((locationId: number) => {
    navigate(`/locations/${locationId}`);
  }, [navigate]);

  // Handle user click
  const handleUserClick = useCallback((userId: string) => {
    navigate("/account");
  }, [navigate]);

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("space-y-4", className)}>
        <div className="text-center py-8">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" onClick={loadInitialData} className="mt-4">
            Opnieuw proberen
          </Button>
        </div>
      </div>
    );
  }

  const hasMore = hasMorePrikbord || hasMoreActivity || hasMorePolls;

  return (
    <div className={cn("space-y-4", className)}>
      <PrikbordComposer onSuccess={handlePostSuccess} />
      <TimelineSubFilters activeFilter={subFilter} onFilterChange={setSubFilter} />

      {timelineItems.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            {subFilter === "all"
              ? "Nog geen content. Deel je eerste post!"
              : subFilter === "polls"
              ? "Er zijn nog geen polls beschikbaar."
              : subFilter === "check_ins"
              ? "Er zijn nog geen check-ins."
              : "Er zijn nog geen notities."}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {timelineItems.map((item) => {
              if (item.type === "prikbord") {
                return (
                  <SharedLinkCard
                    key={`prikbord-${item.data.id}`}
                    link={item.data}
                    onReactionToggle={(reactionType) => handlePrikbordReactionToggle(item.data.id, reactionType)}
                    onDelete={() => handlePrikbordDelete(item.data.id)}
                    reactions={item.data.reactions || null}
                    userReaction={(item.data.user_reaction as ReactionType) || null}
                  />
                );
              } else if (item.type === "activity") {
                const feedCardProps = transformActivityItem(
                  item.data,
                  handleActivityReactionToggle,
                  handleActivityBookmark,
                  t,
                  handleImageClick,
                  handleLocationClick,
                  handleUserClick
                );
                // Skip items that couldn't be transformed (no user or invalid activity type)
                if (!feedCardProps) {
                  return null;
                }
                return <FeedCard key={`activity-${item.data.id}`} {...feedCardProps} />;
              } else if (item.type === "poll") {
                const hasResponded = item.data.user_has_responded || respondedPolls.has(item.data.id);
                return (
                  <PollCard
                    key={`poll-${item.data.id}`}
                    poll={item.data}
                    stats={pollStats[item.data.id]}
                    selectedOption={selectedOptions[item.data.id]}
                    isSubmitting={submittingPolls.has(item.data.id)}
                    hasResponded={hasResponded}
                    onOptionSelect={handlePollOptionSelect}
                    onSubmitVote={handlePollSubmitVote}
                  />
                );
              }
              return null;
            })}
          </div>

          {hasMore && (
            <Button
              variant="outline"
              className="w-full"
              onClick={loadMore}
              disabled={isLoadingMore}
            >
              {isLoadingMore ? "Laden..." : "Meer laden"}
            </Button>
          )}
        </>
      )}
    </div>
  );
}


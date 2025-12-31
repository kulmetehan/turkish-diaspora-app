// Frontend/src/components/feed/PollFeed.tsx
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getPollStats, listPolls, submitPollResponse, type Poll, type PollStats } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

interface PollFeedProps {
  className?: string;
  onPollClick?: (pollId: number) => void;
}

const INITIAL_LIMIT = 50; // Fetch more polls at once

export function PollFeed({ className, onPollClick }: PollFeedProps) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [pollStats, setPollStats] = useState<Record<number, PollStats>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedOptions, setSelectedOptions] = useState<Record<number, number>>({});
  const [submittingPolls, setSubmittingPolls] = useState<Set<number>>(new Set());
  const [respondedPolls, setRespondedPolls] = useState<Set<number>>(new Set());

  const loadPolls = useCallback(async () => {
    setIsLoading(true);
    try {
      const pollsData = await listPolls(undefined, INITIAL_LIMIT);
      setPolls(pollsData);

      // Track which polls user has responded to
      const respondedSet = new Set<number>();
      pollsData.forEach(poll => {
        if (poll.user_has_responded) {
          respondedSet.add(poll.id);
        }
      });
      setRespondedPolls(respondedSet);

      // Fetch stats for polls that user has responded to
      const respondedPolls = pollsData.filter(p => p.user_has_responded);
      const statsPromises = respondedPolls.map(async (poll) => {
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
      toast.error("Kon polls niet laden");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPolls();
  }, [loadPolls]);

  const handleOptionSelect = (pollId: number, optionId: number) => {
    if (respondedPolls.has(pollId) || submittingPolls.has(pollId)) {
      return; // Don't allow selection if already responded or submitting
    }
    setSelectedOptions(prev => ({
      ...prev,
      [pollId]: optionId
    }));
  };

  const handleSubmitVote = async (pollId: number) => {
    const optionId = selectedOptions[pollId];
    if (!optionId || respondedPolls.has(pollId) || submittingPolls.has(pollId)) {
      return;
    }

    try {
      setSubmittingPolls(prev => new Set(prev).add(pollId));
      await submitPollResponse(pollId, optionId);
      
      // Optimistically update state
      setRespondedPolls(prev => new Set(prev).add(pollId));
      
      // Show gamification feedback
      toast.success("Diaspora Nabzı'na katkı sağladın", {
        duration: 3000,
      });

      // Fetch stats immediately for this poll
      try {
        const stats = await getPollStats(pollId);
        setPollStats(prev => ({
          ...prev,
          [pollId]: stats
        }));
      } catch (err) {
        console.error("Failed to load poll stats:", err);
      }

      // Update the poll in the list to mark as responded
      setPolls(prev => prev.map(poll => 
        poll.id === pollId 
          ? { ...poll, user_has_responded: true }
          : poll
      ));

      // Clear selected option
      setSelectedOptions(prev => {
        const next = { ...prev };
        delete next[pollId];
        return next;
      });

      onPollClick?.(pollId);
    } catch (err: any) {
      // If user already responded (409), refresh poll data and show results
      const errorMessage = err.message || "";
      const isAlreadyResponded = 
        err.status === 409 || 
        errorMessage.includes("409") ||
        errorMessage.includes("Already responded") || 
        errorMessage.includes("already");
      
      if (isAlreadyResponded) {
        // Mark as responded and reload polls to get updated status
        setRespondedPolls(prev => new Set(prev).add(pollId));
        // Reload polls to get updated user_has_responded status
        loadPolls();
        // Don't show error toast
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
  };

  if (isLoading) {
    return (
      <div className={cn("space-y-4 mt-2", className)}>
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i} className="h-32 w-full animate-pulse bg-muted/40" />
        ))}
      </div>
    );
  }

  if (polls.length === 0) {
    return (
      <div className={cn("mt-2", className)}>
        <Card className="p-6 text-center">
          <p className="text-muted-foreground">Er zijn nog geen polls beschikbaar.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4 mt-2", className)}>
      {polls.map((poll) => {
        // Use poll.user_has_responded as source of truth, fallback to respondedPolls Set
        const hasResponded = poll.user_has_responded || respondedPolls.has(poll.id);
        const stats = pollStats[poll.id];
        // Always show results if user has responded, even if stats are still loading
        const hasResults = hasResponded;
        const selectedOption = selectedOptions[poll.id];
        const isSubmitting = submittingPolls.has(poll.id);

        return (
          <Card
            key={poll.id}
            className="p-4"
          >
            <div className="space-y-3">
              <div>
                <h3 className="font-gilroy font-semibold text-lg text-foreground">{poll.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{poll.question}</p>
              </div>

              {hasResults ? (
                <div className="space-y-2 pt-2">
                  <p className="text-sm font-gilroy font-medium text-foreground">Resultaten:</p>
                  {poll.options.map((option) => {
                    const count = stats?.option_counts[option.id] || 0;
                    const totalResponses = stats?.total_responses || 0;
                    const percentage = totalResponses > 0
                      ? Math.round((count / totalResponses) * 100)
                      : 0;
                    const isSelected = selectedOption === option.id;
                    return (
                      <div key={option.id} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className={cn(
                            "text-foreground",
                            isSelected && "font-medium"
                          )}>
                            {option.option_text}
                            {isSelected && " ✓"}
                          </span>
                          <span className="text-muted-foreground font-medium">
                            {stats ? `${percentage}%` : "Laden..."}
                          </span>
                        </div>
                        {stats && (
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {stats && (
                    <p className="text-xs text-muted-foreground pt-1">
                      {stats.total_responses} {stats.total_responses === 1 ? "stem" : "stemmen"}
                    </p>
                  )}
                  {!stats && (
                    <p className="text-xs text-muted-foreground pt-1">
                      Resultaten worden geladen...
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2 pt-2">
                  {poll.options.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => handleOptionSelect(poll.id, option.id)}
                      disabled={hasResponded || isSubmitting}
                      className={cn(
                        "w-full text-left p-3 rounded-lg border transition-colors",
                        "hover:border-primary hover:bg-primary/5",
                        "focus:outline-none focus:ring-2 focus:ring-primary/30",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                        selectedOption === option.id
                          ? "border-primary bg-primary/10"
                          : "border-border"
                      )}
                    >
                      {option.option_text}
                    </button>
                  ))}
                  <Button
                    onClick={() => handleSubmitVote(poll.id)}
                    disabled={!selectedOption || hasResponded || isSubmitting}
                    className="w-full"
                  >
                    {isSubmitting ? "Stemmen..." : "Stem"}
                  </Button>
                </div>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}




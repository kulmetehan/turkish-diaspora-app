// Frontend/src/components/feed/PollFeed.tsx
import { Card } from "@/components/ui/card";
import { getPollStats, listPolls, type Poll, type PollStats } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PollModal } from "./PollModal";

interface PollFeedProps {
  className?: string;
  onPollClick?: (pollId: number) => void;
}

const INITIAL_LIMIT = 50; // Fetch more polls at once

export function PollFeed({ className, onPollClick }: PollFeedProps) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [pollStats, setPollStats] = useState<Record<number, PollStats>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPollId, setSelectedPollId] = useState<number | null>(null);
  const [pollModalOpen, setPollModalOpen] = useState(false);

  const loadPolls = useCallback(async () => {
    setIsLoading(true);
    try {
      const pollsData = await listPolls(undefined, INITIAL_LIMIT);
      setPolls(pollsData);

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

  const handlePollClick = (pollId: number) => {
    setSelectedPollId(pollId);
    setPollModalOpen(true);
    onPollClick?.(pollId);
  };

  const handleModalClose = () => {
    setPollModalOpen(false);
    // Reload polls to get updated response status
    loadPolls();
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
    <>
      <div className={cn("space-y-4 mt-2", className)}>
        {polls.map((poll) => {
          const stats = pollStats[poll.id];
          const hasResults = poll.user_has_responded && stats && stats.privacy_threshold_met;

          return (
            <Card
              key={poll.id}
              className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => handlePollClick(poll.id)}
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
                      const count = stats.option_counts[option.id] || 0;
                      const percentage = stats.total_responses > 0
                        ? Math.round((count / stats.total_responses) * 100)
                        : 0;
                      return (
                        <div key={option.id} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="text-foreground">{option.option_text}</span>
                            <span className="text-muted-foreground font-medium">{percentage}%</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    <p className="text-xs text-muted-foreground pt-1">
                      {stats.total_responses} {stats.total_responses === 1 ? "stem" : "stemmen"}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 pt-2">
                    <p className="text-sm text-muted-foreground">Klik om te stemmen</p>
                    <div className="space-y-1">
                      {poll.options.map((option) => (
                        <div
                          key={option.id}
                          className="text-sm text-foreground/70 border border-border rounded p-2"
                        >
                          {option.option_text}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <PollModal
        pollId={selectedPollId}
        open={pollModalOpen}
        onOpenChange={handleModalClose}
      />
    </>
  );
}

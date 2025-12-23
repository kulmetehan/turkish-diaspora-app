// Frontend/src/components/feed/PollModal.tsx
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getPoll, getPollStats, submitPollResponse, type Poll, type PollStats } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface PollModalProps {
  pollId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PollModal({ pollId, open, onOpenChange }: PollModalProps) {
  const [poll, setPoll] = useState<Poll | null>(null);
  const [stats, setStats] = useState<PollStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);

  useEffect(() => {
    if (!open || !pollId) {
      setPoll(null);
      setStats(null);
      setSelectedOption(null);
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [pollData, statsData] = await Promise.all([
          getPoll(pollId),
          getPollStats(pollId).catch(() => null), // Stats may not be available
        ]);

        if (!cancelled) {
          setPoll(pollData);
          setStats(statsData);
        }
      } catch (err) {
        if (!cancelled) {
          toast.error("Poll kon niet worden geladen");
          onOpenChange(false);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [pollId, open, onOpenChange]);

  const handleSubmit = async () => {
    if (!poll || !selectedOption || isSubmitting) return;

    try {
      setIsSubmitting(true);
      await submitPollResponse(poll.id, selectedOption);
      
      // Show gamification feedback message
      toast.success("Diaspora Nabzı'na katkı sağladın", {
        duration: 3000,
      });

      // Fetch updated poll data and stats immediately
      const [updatedPoll, updatedStats] = await Promise.all([
        getPoll(poll.id),
        getPollStats(poll.id).catch(() => null),
      ]);

      // Update state to show results
      setPoll(updatedPoll);
      setStats(updatedStats);
      // Don't close modal - show results instead
    } catch (err) {
      toast.error("Kon niet stemmen");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!pollId) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{poll?.title || "Poll"}</DialogTitle>
          <DialogDescription>{poll?.question}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-muted-foreground">Poll laden...</div>
        ) : poll ? (
          <div className="space-y-4">
            {poll.user_has_responded ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">Je hebt al gestemd op deze poll.</p>
                {stats && (
                  <div className="space-y-2">
                    <p className="text-sm font-gilroy font-medium">Resultaten:</p>
                    {poll.options.map((option) => {
                      const count = stats.option_counts[option.id] || 0;
                      const percentage = stats.total_responses > 0
                        ? Math.round((count / stats.total_responses) * 100)
                        : 0;
                      return (
                        <div key={option.id} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>{option.option_text}</span>
                            <span className="text-muted-foreground">{percentage}%</span>
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
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {poll.options.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setSelectedOption(option.id)}
                    className={cn(
                      "w-full text-left p-3 rounded-lg border transition-colors",
                      "hover:border-primary hover:bg-primary/5",
                      "focus:outline-none focus:ring-2 focus:ring-primary/30",
                      selectedOption === option.id
                        ? "border-primary bg-primary/10"
                        : "border-border"
                    )}
                  >
                    {option.option_text}
                  </button>
                ))}
                <Button
                  onClick={handleSubmit}
                  disabled={!selectedOption || isSubmitting}
                  className="w-full"
                >
                  {isSubmitting ? "Stemmen..." : "Stem"}
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-muted-foreground">Poll kon niet worden geladen</div>
        )}
      </DialogContent>
    </Dialog>
  );
}









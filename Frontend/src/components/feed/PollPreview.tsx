// Frontend/src/components/feed/PollPreview.tsx
import { Button } from "@/components/ui/button";
import { getPoll, getPollStats, submitPollResponse, type Poll, type PollStats } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface PollPreviewProps {
  pollId: number;
  className?: string;
}

export function PollPreview({ pollId, className }: PollPreviewProps) {
  const [poll, setPoll] = useState<Poll | null>(null);
  const [stats, setStats] = useState<PollStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasResponded, setHasResponded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchPoll = async () => {
      try {
        setIsLoading(true);
        setError(false);
        const pollData = await getPoll(pollId);
        
        if (!cancelled) {
          setPoll(pollData);
          setHasResponded(pollData.user_has_responded);
          
          // Always load stats if user has responded
          if (pollData.user_has_responded) {
            try {
              const statsData = await getPollStats(pollId);
              if (!cancelled) {
                setStats(statsData);
              }
            } catch (err) {
              console.error("Failed to load poll stats:", err);
              // Don't show error, just leave stats as null
            }
          } else {
            setStats(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(true);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchPoll();

    return () => {
      cancelled = true;
    };
  }, [pollId]);

  const handleOptionSelect = (optionId: number) => {
    if (hasResponded || isSubmitting) {
      return;
    }
    setSelectedOption(optionId);
  };

  const handleSubmitVote = async () => {
    if (!poll || !selectedOption || hasResponded || isSubmitting) {
      return;
    }

    try {
      setIsSubmitting(true);
      await submitPollResponse(poll.id, selectedOption);
      
      // Optimistically update state
      setHasResponded(true);
      
      // Show gamification feedback
      toast.success("Diaspora Nabzı'na katkı sağladın", {
        duration: 3000,
      });

      // Fetch stats immediately
      try {
        const updatedStats = await getPollStats(poll.id);
        setStats(updatedStats);
      } catch (err) {
        console.error("Failed to load poll stats:", err);
      }

      // Update poll to mark as responded
      setPoll(prev => prev ? { ...prev, user_has_responded: true } : null);
    } catch (err: any) {
      // If user already responded (409), refresh poll data and show results
      const errorMessage = err.message || "";
      const isAlreadyResponded = 
        err.status === 409 || 
        errorMessage.includes("409") ||
        errorMessage.includes("Already responded") || 
        errorMessage.includes("already");
      
      if (isAlreadyResponded) {
        setHasResponded(true);
        // Refresh poll data
        try {
          const updatedPoll = await getPoll(poll.id);
          setPoll(updatedPoll);
          // Fetch stats
          try {
            const updatedStats = await getPollStats(poll.id);
            setStats(updatedStats);
          } catch (statsErr) {
            console.error("Failed to load poll stats:", statsErr);
          }
          // Don't show error toast, just refresh to show results
          return;
        } catch (refreshErr) {
          console.error("Failed to refresh poll after 409:", refreshErr);
        }
      }
      toast.error("Kon niet stemmen");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className={cn("text-sm font-gilroy font-normal text-muted-foreground italic", className)}>
        Poll laden...
      </div>
    );
  }

  if (error || !poll) {
    return (
      <div className={cn("text-sm font-gilroy font-normal text-muted-foreground italic", className)}>
        Poll kon niet worden geladen
      </div>
    );
  }

  // Always show results when user has responded
  const hasResults = hasResponded;

  return (
    <div className={cn("space-y-2 mt-2", className)}>
      <div>
        <h4 className="text-sm font-gilroy font-semibold text-foreground">{poll.title}</h4>
        <p className="text-xs text-muted-foreground mt-0.5">{poll.question}</p>
      </div>

      {hasResults ? (
        <div className="space-y-1.5 pt-1">
          {poll.options.map((option) => {
            const count = stats?.option_counts[option.id] || 0;
            const totalResponses = stats?.total_responses || 0;
            const percentage = totalResponses > 0
              ? Math.round((count / totalResponses) * 100)
              : 0;
            const isSelected = selectedOption === option.id;
            return (
              <div key={option.id} className="space-y-0.5">
                <div className="flex justify-between text-xs">
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
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
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
            <p className="text-xs text-muted-foreground pt-0.5">
              {stats.total_responses} {stats.total_responses === 1 ? "stem" : "stemmen"}
            </p>
          )}
          {!stats && (
            <p className="text-xs text-muted-foreground pt-0.5">
              Resultaten worden geladen...
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-1.5 pt-1">
          {poll.options.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => handleOptionSelect(option.id)}
              disabled={hasResponded || isSubmitting}
              className={cn(
                "w-full text-left p-2 rounded-lg border text-xs transition-colors",
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
            onClick={handleSubmitVote}
            disabled={!selectedOption || hasResponded || isSubmitting}
            size="sm"
            className="w-full text-xs"
          >
            {isSubmitting ? "Stemmen..." : "Stem"}
          </Button>
        </div>
      )}
    </div>
  );
}









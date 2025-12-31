// Frontend/src/components/polls/PollCard.tsx
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { submitPollResponse, getPollStats, getPoll, type Poll, type PollStats } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { nl } from "date-fns/locale";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { deleteAdminPoll } from "@/lib/apiAdmin";

interface PollCardProps {
  poll: Poll;
  onResponse?: () => void;
  className?: string;
}

export function PollCard({ poll, onResponse, className }: PollCardProps) {
  const { isAdmin } = useAdminAuth();
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasResponded, setHasResponded] = useState(poll.user_has_responded);
  const [stats, setStats] = useState<PollStats | null>(null);
  const [showStats, setShowStats] = useState(false);

  // Sync hasResponded with poll.user_has_responded when poll prop changes
  useEffect(() => {
    setHasResponded(poll.user_has_responded);
  }, [poll.user_has_responded]);

  useEffect(() => {
    if (hasResponded) {
      loadStats();
    } else {
      // Reset stats when poll is not responded to
      setStats(null);
      setShowStats(false);
    }
  }, [hasResponded, poll.id]);

  const loadStats = async () => {
    try {
      const pollStats = await getPollStats(poll.id);
      setStats(pollStats);
      // Always show stats if user has responded
      setShowStats(true);
    } catch (err) {
      console.error("Failed to load poll stats:", err);
      // Still show stats UI even if loading failed, so user knows they've responded
      setShowStats(true);
    }
  };

  const handleSubmit = async () => {
    if (!selectedOptionId) return;

    setIsSubmitting(true);
    try {
      await submitPollResponse(poll.id, selectedOptionId);
      setHasResponded(true);
      toast.success("Stem opgeslagen!");
      if (onResponse) {
        onResponse();
      }
      await loadStats();
    } catch (err: any) {
      // If user already responded (409), refresh poll data and show results
      const errorMessage = err.message || "";
      const isAlreadyResponded = 
        err.status === 409 || 
        errorMessage.includes("409") ||
        errorMessage.includes("Already responded") || 
        errorMessage.includes("already");
      
      if (isAlreadyResponded) {
        // Refresh poll data to get updated user_has_responded status
        try {
          const updatedPoll = await getPoll(poll.id);
          // Update local state
          setHasResponded(updatedPoll.user_has_responded);
          await loadStats();
          // Notify parent to refresh poll list
          if (onResponse) {
            onResponse();
          }
          // Don't show error toast, just silently refresh to show results
          return;
        } catch (refreshErr) {
          console.error("Failed to refresh poll after 409:", refreshErr);
          // Fallback: just mark as responded locally
          setHasResponded(true);
          await loadStats();
          if (onResponse) {
            onResponse();
          }
          return;
        }
      }
      const message = errorMessage || "Kon stem niet opslaan";
      toast.error("Fout", { description: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalResponses = stats?.total_responses || 0;
  const maxCount = stats ? Math.max(...Object.values(stats.option_counts || {}), 0) : 0;

  const handleAdminDelete = async () => {
    if (!confirm("Weet je zeker dat je deze poll wilt verwijderen?")) {
      return;
    }

    try {
      await deleteAdminPoll(poll.id);
      toast.success("Poll verwijderd");
      // Refresh page or call callback if provided
      window.location.reload();
    } catch (err: any) {
      toast.error("Kon poll niet verwijderen", {
        description: err.message || "Er is een fout opgetreden",
      });
    }
  };

  return (
    <Card className={cn("rounded-xl border border-border/80 bg-card shadow-soft", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg font-semibold">{poll.title}</CardTitle>
          <div className="flex items-center gap-2">
            {poll.is_sponsored && (
              <Badge variant="secondary" className="text-xs">
                <Icon name="Star" className="h-3 w-3 mr-1" />
                Gesponsord
              </Badge>
            )}
            {isAdmin && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleAdminDelete}
                className="text-destructive hover:text-destructive shrink-0"
                aria-label="Verwijder als admin"
              >
                <Icon name="Trash2" className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{poll.question}</p>
        {poll.ends_at && (
          <p className="text-xs text-muted-foreground mt-1">
            Tot {format(new Date(poll.ends_at), "d MMMM yyyy", { locale: nl })}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {!hasResponded ? (
          <>
            <div className="space-y-2">
              {poll.options.map((option) => (
                <Button
                  key={option.id}
                  variant={selectedOptionId === option.id ? "default" : "outline"}
                  className={cn(
                    "w-full justify-start text-left h-auto py-3 px-4",
                    selectedOptionId === option.id && "bg-primary text-primary-foreground"
                  )}
                  onClick={() => setSelectedOptionId(option.id)}
                  disabled={isSubmitting}
                >
                  <div className="flex items-center gap-3 w-full">
                    <div
                      className={cn(
                        "h-5 w-5 rounded-full border-2 flex items-center justify-center flex-shrink-0",
                        selectedOptionId === option.id
                          ? "border-primary-foreground bg-primary-foreground"
                          : "border-border"
                      )}
                    >
                      {selectedOptionId === option.id && (
                        <Icon name="Check" className="h-3 w-3 text-primary" />
                      )}
                    </div>
                    <span className="flex-1">{option.option_text}</span>
                  </div>
                </Button>
              ))}
            </div>
            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!selectedOptionId || isSubmitting}
            >
              {isSubmitting ? "Opslaan..." : "Stem"}
            </Button>
          </>
        ) : (
          <>
            {/* Always show results when user has responded */}
            <div className="space-y-2">
              {poll.options.map((option) => {
                const count = stats?.option_counts[option.id] || 0;
                const percentage = totalResponses > 0 ? (count / totalResponses) * 100 : 0;
                const isSelected = selectedOptionId === option.id;

                return (
                  <div
                    key={option.id}
                    className={cn(
                      "rounded-lg border-2 p-3 transition-colors",
                      isSelected
                        ? "border-primary bg-primary/10"
                        : "border-border bg-muted/30"
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{option.option_text}</span>
                      <span className="text-xs text-muted-foreground">
                        {stats ? (
                          <>
                            {count} ({percentage.toFixed(1)}%)
                          </>
                        ) : (
                          "Laden..."
                        )}
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
            </div>
            {stats && (
              <p className="text-xs text-muted-foreground text-center">
                Totaal {totalResponses} {totalResponses === 1 ? "stem" : "stemmen"}
              </p>
            )}
            {!stats && (
              <p className="text-xs text-muted-foreground text-center">
                Resultaten worden geladen...
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}


























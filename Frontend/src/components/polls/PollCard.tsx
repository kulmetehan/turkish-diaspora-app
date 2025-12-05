// Frontend/src/components/polls/PollCard.tsx
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { submitPollResponse, getPollStats, type Poll, type PollStats } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { nl } from "date-fns/locale";

interface PollCardProps {
  poll: Poll;
  onResponse?: () => void;
  className?: string;
}

export function PollCard({ poll, onResponse, className }: PollCardProps) {
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasResponded, setHasResponded] = useState(poll.user_has_responded);
  const [stats, setStats] = useState<PollStats | null>(null);
  const [showStats, setShowStats] = useState(false);

  useEffect(() => {
    if (hasResponded) {
      loadStats();
    }
  }, [hasResponded, poll.id]);

  const loadStats = async () => {
    try {
      const pollStats = await getPollStats(poll.id);
      setStats(pollStats);
      setShowStats(pollStats.privacy_threshold_met);
    } catch (err) {
      console.error("Failed to load poll stats:", err);
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
      const message = err.message || "Kon stem niet opslaan";
      toast.error("Fout", { description: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalResponses = stats?.total_responses || 0;
  const maxCount = stats ? Math.max(...Object.values(stats.option_counts || {}), 0) : 0;

  return (
    <Card className={cn("rounded-xl border border-border/80 bg-card shadow-soft", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg font-semibold">{poll.title}</CardTitle>
          {poll.is_sponsored && (
            <Badge variant="secondary" className="text-xs">
              <Icon name="Star" className="h-3 w-3 mr-1" />
              Gesponsord
            </Badge>
          )}
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
                      {showStats && (
                        <span className="text-xs text-muted-foreground">
                          {count} ({percentage.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                    {showStats && (
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
            {showStats && (
              <p className="text-xs text-muted-foreground text-center">
                Totaal {totalResponses} {totalResponses === 1 ? "stem" : "stemmen"}
              </p>
            )}
            {!showStats && totalResponses > 0 && (
              <p className="text-xs text-muted-foreground text-center">
                Resultaten worden getoond bij 10+ stemmen ({totalResponses}/10)
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}



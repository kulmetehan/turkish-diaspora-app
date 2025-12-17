// Frontend/src/pages/PollDetailPage.tsx
import { AppViewportShell } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { getPoll, getPollStats, submitPollResponse, type Poll, type PollStats } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

export default function PollDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const pollId = id ? parseInt(id, 10) : null;

  const [poll, setPoll] = useState<Poll | null>(null);
  const [stats, setStats] = useState<PollStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);

  useEffect(() => {
    if (!pollId || isNaN(pollId)) {
      toast.error("Ongeldige poll ID");
      navigate("/#/feed");
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [pollData, statsData] = await Promise.all([
          getPoll(pollId),
          getPollStats(pollId).catch(() => null),
        ]);

        if (!cancelled) {
          setPoll(pollData);
          setStats(statsData);
        }
      } catch (err) {
        if (!cancelled) {
          toast.error("Poll kon niet worden geladen");
          navigate("/#/feed");
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
  }, [pollId, navigate]);

  const handleSubmit = async () => {
    if (!poll || !selectedOption || isSubmitting) return;

    try {
      setIsSubmitting(true);
      await submitPollResponse(poll.id, selectedOption);
      toast.success("Je stem is opgeslagen!");
      // Refresh poll data
      const [updatedPoll, updatedStats] = await Promise.all([
        getPoll(poll.id),
        getPollStats(poll.id).catch(() => null),
      ]);
      setPoll(updatedPoll);
      setStats(updatedStats);
    } catch (err) {
      toast.error("Kon niet stemmen");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <AppViewportShell variant="content">
        <div className="flex items-center justify-center min-h-[50vh]">
          <p className="text-muted-foreground">Poll laden...</p>
        </div>
      </AppViewportShell>
    );
  }

  if (!poll) {
    return (
      <AppViewportShell variant="content">
        <div className="flex items-center justify-center min-h-[50vh]">
          <p className="text-muted-foreground">Poll niet gevonden</p>
        </div>
      </AppViewportShell>
    );
  }

  return (
    <AppViewportShell variant="content">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center gap-4 p-4 border-b border-border">
          <button
            type="button"
            onClick={() => navigate("/#/feed")}
            className="p-2 hover:bg-muted rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30"
            aria-label="Terug"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold">Poll</h1>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">{poll.title}</h2>
            <p className="text-lg text-muted-foreground">{poll.question}</p>
          </div>

          {poll.user_has_responded ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Je hebt al gestemd op deze poll.</p>
              {stats && stats.privacy_threshold_met ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-2">
                      Resultaten ({stats.total_responses} stemmen):
                    </p>
                    <div className="space-y-3">
                      {poll.options.map((option) => {
                        const count = stats.option_counts[option.id] || 0;
                        const percentage = stats.total_responses > 0
                          ? Math.round((count / stats.total_responses) * 100)
                          : 0;
                        return (
                          <div key={option.id} className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium">{option.option_text}</span>
                              <span className="text-muted-foreground">
                                {count} stemmen ({percentage}%)
                              </span>
                            </div>
                            <div className="h-3 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Resultaten worden getoond wanneer er minimaal 10 stemmen zijn.
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm font-medium">Kies een optie:</p>
              <div className="space-y-2">
                {poll.options.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setSelectedOption(option.id)}
                    className={cn(
                      "w-full text-left p-4 rounded-lg border transition-colors",
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
              </div>
              <Button
                onClick={handleSubmit}
                disabled={!selectedOption || isSubmitting}
                className="w-full"
                size="lg"
              >
                {isSubmitting ? "Stemmen..." : "Stem"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </AppViewportShell>
  );
}


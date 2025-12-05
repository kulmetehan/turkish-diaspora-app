// Frontend/src/components/polls/PollsFeed.tsx
import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PollCard } from "./PollCard";
import { listPolls, type Poll } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/ui/cn";

interface PollsFeedProps {
  cityKey?: string;
  limit?: number;
  className?: string;
}

export function PollsFeed({ cityKey, limit = 10, className }: PollsFeedProps) {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPolls();
  }, [cityKey, limit]);

  const loadPolls = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listPolls(cityKey, limit);
      setPolls(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Kon polls niet laden";
      setError(message);
      toast.error("Fout bij het laden van polls", { description: message });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePollResponse = () => {
    // Reload polls to update response status
    loadPolls();
  };

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        {Array.from({ length: 2 }).map((_, index) => (
          <Skeleton key={index} className="h-64 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("rounded-xl border border-border/80 bg-card p-5 text-center shadow-soft", className)}>
        <p className="text-foreground">{error}</p>
        <Button
          size="sm"
          className="mt-4"
          onClick={loadPolls}
          variant="outline"
        >
          Opnieuw proberen
        </Button>
      </div>
    );
  }

  if (polls.length === 0) {
    return (
      <div className={cn("rounded-xl border border-border/80 bg-card p-6 text-center text-muted-foreground shadow-soft", className)}>
        <p>Er zijn op dit moment geen actieve polls.</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {polls.map((poll) => (
        <PollCard key={poll.id} poll={poll} onResponse={handlePollResponse} />
      ))}
    </div>
  );
}


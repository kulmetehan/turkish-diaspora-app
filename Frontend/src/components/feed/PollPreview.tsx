// Frontend/src/components/feed/PollPreview.tsx
import { getPoll, type Poll } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useEffect, useState } from "react";

interface PollPreviewProps {
  pollId: number;
  onOpenModal?: (pollId: number) => void;
  className?: string;
}

export function PollPreview({ pollId, onOpenModal, className }: PollPreviewProps) {
  const [poll, setPoll] = useState<Poll | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchPoll = async () => {
      try {
        setIsLoading(true);
        setError(false);
        const pollData = await getPoll(pollId);
        if (!cancelled) {
          setPoll(pollData);
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

  const handleClick = () => {
    if (onOpenModal) {
      onOpenModal(pollId);
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

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "text-sm font-gilroy font-normal text-muted-foreground italic hover:text-primary hover:underline text-left transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 rounded",
        className
      )}
    >
      "{poll.question}"
    </button>
  );
}



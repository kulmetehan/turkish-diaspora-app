// Frontend/src/components/feed/EmojiReactions.tsx
import { EmojiPicker } from "@/components/ui/EmojiPicker";
import { type ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useMemo, useState } from "react";

export interface EmojiReactionsProps {
  activityId: number;
  reactions: Record<string, number> | null;
  userReaction: ReactionType | null;
  onReactionToggle: (reactionType: ReactionType) => void;
  className?: string;
}

export function EmojiReactions({
  activityId,
  reactions,
  userReaction,
  onReactionToggle,
  className,
}: EmojiReactionsProps) {
  const [isToggling, setIsToggling] = useState<ReactionType | null>(null);

  const handleReactionClick = async (e: React.MouseEvent, reactionType: ReactionType) => {
    e.stopPropagation(); // Prevent event from bubbling to parent click handlers
    if (isToggling) return; // Prevent double clicks

    setIsToggling(reactionType);
    try {
      await onReactionToggle(reactionType);
    } finally {
      setIsToggling(null);
    }
  };

  // Convert reactions to array of entries, filter out zero counts, sort by count desc
  // Memoize to prevent unnecessary re-renders when reactions object reference changes
  const reactionEntries = useMemo(() => {
    if (!reactions) return [];
    return Object.entries(reactions)
      .filter(([_, count]) => count > 0)
      .sort(([_, a], [__, b]) => b - a);
  }, [reactions]);

  return (
    <div className={cn("flex items-center gap-2 flex-wrap", className)}>
      {reactionEntries.map(([emoji, count]) => {
        const isActive = userReaction === emoji;
        const isLoading = isToggling === emoji;

        return (
          <button
            key={`${activityId}-${emoji}`}
            type="button"
            onClick={(e) => handleReactionClick(e, emoji)}
            disabled={isLoading}
            className={cn(
              "flex items-center gap-1 px-2 py-1.5 rounded-lg transition-all",
              "hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/30",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              isActive
                ? "bg-primary/10 text-primary border border-primary/30 scale-110"
                : "bg-transparent"
            )}
            aria-label={`${emoji} reaction`}
            title={emoji}
          >
            <span className="text-lg leading-none">{emoji}</span>
            {count > 0 && (
              <span
                className={cn(
                  "text-xs font-gilroy font-medium",
                  isActive ? "text-primary" : "text-muted-foreground"
                )}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
      <div onClick={(e) => e.stopPropagation()}>
        <EmojiPicker
          onEmojiSelect={async (emoji) => {
            // EmojiPicker doesn't pass event, but wrapper div stops propagation
            if (isToggling) return;
            setIsToggling(emoji as ReactionType);
            try {
              const result = onReactionToggle(emoji as ReactionType);
              // Handle both sync and async callbacks
              if (result && typeof result.then === 'function') {
                await result;
              }
            } finally {
              setIsToggling(null);
            }
          }}
          className="text-foreground"
        />
      </div>
    </div>
  );
}










// Frontend/src/components/feed/EmojiReactions.tsx
import { EmojiPicker } from "@/components/ui/EmojiPicker";
import { type ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useState } from "react";

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

  const handleReactionClick = async (reactionType: ReactionType) => {
    if (isToggling) return; // Prevent double clicks

    setIsToggling(reactionType);
    try {
      await onReactionToggle(reactionType);
    } finally {
      setIsToggling(null);
    }
  };

  // Convert reactions to array of entries, filter out zero counts, sort by count desc
  const reactionEntries = reactions
    ? Object.entries(reactions)
      .filter(([_, count]) => count > 0)
      .sort(([_, a], [__, b]) => b - a)
    : [];

  return (
    <div className={cn("flex items-center gap-2 flex-wrap", className)}>
      {reactionEntries.map(([emoji, count]) => {
        const isActive = userReaction === emoji;
        const isLoading = isToggling === emoji;

        return (
          <button
            key={emoji}
            type="button"
            onClick={() => handleReactionClick(emoji)}
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
      <EmojiPicker
        onEmojiSelect={handleReactionClick}
        className="text-foreground"
      />
    </div>
  );
}




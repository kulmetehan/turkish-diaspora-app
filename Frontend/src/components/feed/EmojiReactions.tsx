// Frontend/src/components/feed/EmojiReactions.tsx
import { type ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { useState } from "react";

export interface EmojiReactionsProps {
  activityId: number;
  reactions: Record<ReactionType, number>;
  userReaction: ReactionType | null;
  onReactionToggle: (reactionType: ReactionType) => void;
  className?: string;
}

const EMOJI_SET: ReactionType[] = ["fire", "heart", "thumbs_up", "smile", "star", "flag"];

const EMOJI_MAP: Record<ReactionType, string> = {
  fire: "🔥",
  heart: "❤️",
  thumbs_up: "👍",
  smile: "😊",
  star: "⭐",
  flag: "🚩",
};

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

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {EMOJI_SET.map((reactionType) => {
        const count = reactions[reactionType] || 0;
        const isActive = userReaction === reactionType;
        const isLoading = isToggling === reactionType;

        return (
          <button
            key={reactionType}
            type="button"
            onClick={() => handleReactionClick(reactionType)}
            disabled={isLoading}
            className={cn(
              "flex items-center gap-1 px-2 py-1.5 rounded-lg transition-all",
              "hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/30",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              isActive
                ? "bg-primary/10 scale-110"
                : "bg-transparent"
            )}
            aria-label={`${reactionType} reaction`}
            title={reactionType}
          >
            <span className="text-lg leading-none">{EMOJI_MAP[reactionType]}</span>
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
    </div>
  );
}


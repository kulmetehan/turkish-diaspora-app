// Frontend/src/components/feed/FeedCard.tsx
import type { ActivityItem, ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { Bookmark } from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { EmojiReactions } from "./EmojiReactions";
import { EventBadge } from "./EventBadge";
import { PollPreview } from "./PollPreview";

export interface FeedCardProps {
  id: number;
  user: {
    avatar: string | null;
    name: string;
  };
  locationName: string | null;
  locationId?: number | null;
  timestamp: string;
  contentText: string;
  noteContent?: string | null;
  pollId?: number | null;
  mediaUrl?: string | null;
  likeCount: number;
  isLiked: boolean;
  isBookmarked: boolean;
  reactions?: Record<ReactionType, number> | null;
  userReaction?: ReactionType | null;
  type: ActivityItem["activity_type"];
  isPromoted?: boolean;
  onReactionToggle?: (reactionType: ReactionType) => void;
  onBookmark?: () => void;
  onClick?: () => void;
  onImageClick?: (imageUrl: string) => void;
  onLocationClick?: (locationId: number) => void;
  onPollClick?: (pollId: number) => void;
  className?: string;
}

function formatActivityTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) {
    return "zojuist";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} min geleden`;
  } else if (diffHours < 24) {
    return `${diffHours} uur geleden`;
  } else {
    // >= 24 uur: exacte datum
    const year = date.getFullYear();
    const currentYear = now.getFullYear();
    try {
      return new Intl.DateTimeFormat("nl-NL", {
        day: "numeric",
        month: "short",
        year: year !== currentYear ? "numeric" : undefined,
      }).format(date);
    } catch {
      return date.toLocaleDateString("nl-NL");
    }
  }
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

export function FeedCard({
  id,
  user,
  locationName,
  locationId,
  timestamp,
  contentText,
  noteContent,
  pollId,
  mediaUrl,
  likeCount,
  isLiked,
  isBookmarked,
  reactions,
  userReaction,
  type,
  isPromoted,
  onReactionToggle,
  onBookmark,
  onClick,
  onImageClick,
  onLocationClick,
  onPollClick,
  className,
}: FeedCardProps) {
  const navigate = useNavigate();
  const timeLabel = useMemo(() => formatActivityTime(timestamp), [timestamp]);
  const hasMedia = Boolean(mediaUrl);
  const isEvent = type === "event";

  // Initialize reactions with all types set to 0 if not provided
  const reactionCounts = useMemo(() => {
    const defaultReactions: Record<ReactionType, number> = {
      fire: 0,
      heart: 0,
      thumbs_up: 0,
      smile: 0,
      star: 0,
      flag: 0,
    };
    return reactions ? { ...defaultReactions, ...reactions } : defaultReactions;
  }, [reactions]);

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation();
    onBookmark?.();
  };

  const handleClick = () => {
    onClick?.();
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick();
    }
  };

  const handleLocationClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (locationId && onLocationClick) {
      onLocationClick(locationId);
    } else if (locationId) {
      navigate(`/#/locations/${locationId}`);
    }
  };

  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "rounded-xl bg-card overflow-hidden",
        "border border-border/50 shadow-soft",
        "transition-all duration-200 ease-in-out",
        "hover:border-border/30 hover:shadow-[0_2px_6px_rgba(15,23,42,0.02),0_1px_2px_rgba(15,23,42,0.01)]",
        onClick && "cursor-pointer",
        onClick && "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
        className
      )}
    >
      {/* Header: Avatar + Name + Meta */}
      <div className="flex items-start gap-3 p-4">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.name}
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-sm">
              {getInitials(user.name)}
            </div>
          )}
        </div>

        {/* Name + Meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-gilroy font-medium text-foreground">{user.name}</p>
            {locationName && (
              <>
                <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
                {locationId ? (
                  <button
                    type="button"
                    onClick={handleLocationClick}
                    className="text-xs text-muted-foreground truncate hover:text-primary hover:underline font-gilroy font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 rounded"
                  >
                    {locationName}
                  </button>
                ) : (
                  <p className="text-xs font-gilroy font-normal text-muted-foreground truncate">{locationName}</p>
                )}
              </>
            )}
            <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
            <p className="text-xs font-gilroy font-normal text-muted-foreground">{timeLabel}</p>
          </div>
          {isPromoted && (
            <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-gilroy font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 mt-1">
              Promoted
            </span>
          )}
        </div>
      </div>

      {/* Content Text */}
      {contentText && (
        <div className="px-4 pb-3">
          {type === "note" && noteContent ? (
            <div className="space-y-1">
              <p className="text-sm font-gilroy font-normal text-foreground">{contentText.split(":")[0]}:</p>
              <p className="text-sm font-gilroy font-normal text-foreground/90">
                {noteContent.length > 150 ? (
                  <>
                    {noteContent.substring(0, 150)}
                    <span className="text-muted-foreground">...</span>
                    {locationId && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onLocationClick && locationId) {
                            onLocationClick(locationId);
                          }
                        }}
                        className="text-primary hover:underline font-gilroy font-medium ml-1 focus:outline-none focus:ring-2 focus:ring-primary/30 rounded"
                      >
                        Lees meer
                      </button>
                    )}
                  </>
                ) : (
                  noteContent
                )}
              </p>
            </div>
          ) : type === "poll_response" && pollId ? (
            <div className="space-y-1">
              <p className="text-sm font-gilroy font-normal text-foreground">{contentText}</p>
              <PollPreview pollId={pollId} onOpenModal={onPollClick} />
            </div>
          ) : (
            <p className="text-sm font-gilroy font-normal text-foreground">{contentText}</p>
          )}
        </div>
      )}

      {/* Media Image */}
      {hasMedia && (
        <div className="relative w-full aspect-video max-h-[400px]">
          {isEvent && <EventBadge />}
          <img
            src={mediaUrl!}
            alt=""
            className="w-full h-full object-cover cursor-pointer"
            loading="lazy"
            onClick={(e) => {
              e.stopPropagation();
              onImageClick?.(mediaUrl!);
            }}
            onError={(e) => {
              // Hide image on error
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
      )}

      {/* Action Row: Emoji Reactions + Bookmark */}
      <div className="flex items-center justify-between gap-4 px-4 py-3 border-t border-border/50">
        {onReactionToggle ? (
          <EmojiReactions
            activityId={id}
            reactions={reactionCounts}
            userReaction={userReaction || null}
            onReactionToggle={onReactionToggle}
          />
        ) : (
          <div /> // Spacer
        )}

        <button
          type="button"
          onClick={handleBookmark}
          className={cn(
            "flex items-center text-sm transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 rounded",
            isBookmarked
              ? "text-primary hover:text-primary/80"
              : "text-muted-foreground hover:text-foreground"
          )}
          aria-label={isBookmarked ? "Remove bookmark" : "Bookmark"}
        >
          <Bookmark
            className={cn(
              "w-5 h-5",
              isBookmarked && "fill-current"
            )}
          />
        </button>
      </div>
    </div>
  );
}




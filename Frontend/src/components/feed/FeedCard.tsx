// Frontend/src/components/feed/FeedCard.tsx
import type { ActivityItem, ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { roleDisplayName } from "@/lib/roleDisplay";
import { labelDisplayName } from "@/lib/labelDisplay";
import { Bookmark } from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { EmojiReactions } from "./EmojiReactions";
import { EventBadge } from "./EventBadge";
import { PollPreview } from "./PollPreview";
import { ReportButton } from "@/components/report/ReportButton";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { deleteAdminCheckIn, deleteAdminNote } from "@/lib/apiAdmin";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { toast } from "sonner";

export interface FeedCardProps {
  id: number;
  user: {
    avatar: string | null;
    name: string;
    primary_role?: string | null;
    secondary_role?: string | null;
    id?: string | null;
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
  labels?: string[] | null;
  onReactionToggle?: (reactionType: ReactionType) => void;
  onBookmark?: () => void;
  onImageClick?: (imageUrl: string) => void;
  onLocationClick?: (locationId: number) => void;
  onPollClick?: (pollId: number) => void;
  onUserClick?: (userId: string) => void;
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

function getInitials(name: string | null | undefined): string {
  if (!name || typeof name !== "string") {
    return "??";
  }
  const trimmed = name.trim();
  if (!trimmed) {
    return "??";
  }
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return trimmed.substring(0, 2).toUpperCase();
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
  labels,
  onReactionToggle,
  onBookmark,
  onImageClick,
  onLocationClick,
  onPollClick,
  onUserClick,
  className,
}: FeedCardProps) {
  const navigate = useNavigate();
  const { isAdmin } = useAdminAuth();
  const timeLabel = useMemo(() => formatActivityTime(timestamp), [timestamp]);
  const hasMedia = Boolean(mediaUrl);
  const isEvent = type === "event";

  // Reactions are now dynamic emoji strings, so we just use them directly
  const reactionCounts = useMemo(() => {
    return reactions || {};
  }, [reactions]);

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation();
    onBookmark?.();
  };

  const handleLocationClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (locationId && onLocationClick) {
      onLocationClick(locationId);
    } else if (locationId) {
      navigate(`/locations/${locationId}`);
    }
  };

  const handleUserClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (user.id && onUserClick) {
      onUserClick(user.id);
    } else if (user.id) {
      navigate("/account");
    }
  };

  const handleAdminDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Weet je zeker dat je dit item wilt verwijderen?")) {
      return;
    }

    try {
      if (type === "check_in") {
        await deleteAdminCheckIn(id);
        toast.success("Check-in verwijderd");
      } else if (type === "note") {
        await deleteAdminNote(id);
        toast.success("Notitie verwijderd");
      }
      // Refresh page or call callback if provided
      window.location.reload();
    } catch (err: any) {
      toast.error("Kon item niet verwijderen", {
        description: err.message || "Er is een fout opgetreden",
      });
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl bg-card overflow-hidden",
        "border border-border/50 shadow-soft",
        "transition-all duration-200 ease-in-out",
        "hover:border-border/30 hover:shadow-[0_2px_6px_rgba(15,23,42,0.02),0_1px_2px_rgba(15,23,42,0.01)]",
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
              className="w-10 h-10 rounded-full object-cover cursor-pointer"
              onClick={handleUserClick}
            />
          ) : (
            <div 
              className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-sm cursor-pointer"
              onClick={handleUserClick}
            >
              {getInitials(user.name)}
            </div>
          )}
        </div>

        {/* Name + Meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={handleUserClick}
              className="text-sm font-gilroy font-medium text-foreground hover:text-primary hover:underline transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 rounded"
            >
              {user.name || "Anonieme gebruiker"}
            </button>
            {user.primary_role && (
              <>
                <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
                <p className="text-xs font-gilroy font-normal text-muted-foreground">
                  {roleDisplayName(user.primary_role)}
                </p>
              </>
            )}
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

        {/* Admin Delete Button */}
        {isAdmin && (type === "check_in" || type === "note") && (
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
              {labels && labels.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap mt-2">
                  {labels.map((label) => (
                    <span
                      key={label}
                      className="inline-flex items-center rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-xs font-gilroy font-medium text-muted-foreground"
                    >
                      {labelDisplayName(label)}
                    </span>
                  ))}
                </div>
              )}
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

      {/* Action Row: Emoji Reactions + Report + Bookmark */}
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

        <div className="flex items-center gap-2">
          {(() => {
            // Determine report type based on activity type
            let reportType: "check_in" | "note" | "poll" | null = null;
            let reportTargetId = id;
            
            if (type === "check_in") {
              reportType = "check_in";
            } else if (type === "note") {
              reportType = "note";
            } else if (type === "poll_response" && pollId) {
              reportType = "poll";
              reportTargetId = pollId;
            }
            
            if (reportType) {
              return (
                <ReportButton
                  reportType={reportType}
                  targetId={reportTargetId}
                  targetName={locationName || contentText || undefined}
                  size="sm"
                  variant="ghost"
                />
              );
            }
            return null;
          })()}
          
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
    </div>
  );
}











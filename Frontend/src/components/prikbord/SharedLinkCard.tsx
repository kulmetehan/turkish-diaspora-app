// Frontend/src/components/prikbord/SharedLinkCard.tsx
import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import type { SharedLink } from "@/types/prikbord";
import { bookmarkSharedLink } from "@/lib/api/prikbord";
import { toast } from "sonner";
import { Bookmark } from "lucide-react";
import { roleDisplayName } from "@/lib/roleDisplay";
import { EmojiReactions } from "@/components/feed/EmojiReactions";
import type { ReactionType } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { ReportButton } from "@/components/report/ReportButton";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useUserAuth } from "@/hooks/useUserAuth";
import { deleteAdminSharedLink } from "@/lib/apiAdmin";
import { ImageModal } from "@/components/feed/ImageModal";

interface SharedLinkCardProps {
  link: SharedLink;
  onDetailClick?: () => void;
  onDelete?: () => void;
  className?: string;
  showDelete?: boolean;
  onReactionToggle?: (reactionType: ReactionType) => void;
  reactions?: Record<ReactionType, number> | null;
  userReaction?: ReactionType | null;
  onUserClick?: (userId: string) => void;
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

export function SharedLinkCard({
  link,
  onDetailClick,
  onDelete,
  className,
  showDelete = false,
  onReactionToggle,
  reactions,
  userReaction,
  onUserClick,
}: SharedLinkCardProps) {
  const navigate = useNavigate();
  const { isAdmin } = useAdminAuth();
  const { user } = useUserAuth();
  const [isBookmarked, setIsBookmarked] = useState(link.is_bookmarked);
  const [isTogglingBookmark, setIsTogglingBookmark] = useState(false);
  const [imageModalUrl, setImageModalUrl] = useState<string | null>(null);
  const [imageModalOpen, setImageModalOpen] = useState(false);

  const timeLabel = useMemo(() => formatActivityTime(link.created_at), [link.created_at]);
  
  // Check if current user is the owner of this post
  const isOwner = useMemo(() => {
    if (!user?.id) return false;
    return link.creator.type === "user" && link.creator.id === user.id;
  }, [user?.id, link.creator]);

  const handleBookmark = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isTogglingBookmark) return;
    
    setIsTogglingBookmark(true);
    try {
      const result = await bookmarkSharedLink(link.id);
      setIsBookmarked(result.bookmarked);
    } catch (err: any) {
      toast.error("Kon bookmark niet updaten", {
        description: err.message || "Er is een fout opgetreden",
      });
    } finally {
      setIsTogglingBookmark(false);
    }
  };

  const handleOpenLink = (e: React.MouseEvent) => {
    e.stopPropagation();
    // For media posts, don't open URL - it's just a placeholder
    if (link.post_type === "media") {
      return;
    }
    window.open(link.url, "_blank", "noopener,noreferrer");
  };

  const handleImageClick = (mediaUrl: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setImageModalUrl(mediaUrl);
    setImageModalOpen(true);
  };

  // Get display title for media posts (don't show URL or fallback)
  const displayTitle = useMemo(() => {
    if (link.post_type === "media") {
      return link.title || null; // Don't show fallback for media posts
    }
    return link.title || link.url;
  }, [link.post_type, link.title, link.url]);

  const handleUserClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (link.creator.id && onUserClick) {
      onUserClick(link.creator.id);
    } else if (link.creator.id) {
      navigate("/account");
    }
  };

  const handleAdminDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Weet je zeker dat je deze link wilt verwijderen?")) {
      return;
    }

    try {
      await deleteAdminSharedLink(link.id);
      toast.success("Link verwijderd");
      // Use callback if provided, otherwise fallback to reload
      if (onDelete) {
        onDelete();
      } else {
        // Fallback: only reload if no callback provided
        window.location.reload();
      }
    } catch (err: any) {
      toast.error("Kon link niet verwijderen", {
        description: err.message || "Er is een fout opgetreden",
      });
    }
  };

  const reactionCounts = useMemo(() => {
    return reactions || {};
  }, [reactions]);

  const creatorName = link.creator.name || "Anonieme gebruiker";

  return (
    <div
      className={cn(
        "rounded-xl bg-card overflow-hidden",
        "border border-border/50 shadow-soft",
        "transition-all duration-200 ease-in-out",
        "hover:border-border/30 hover:shadow-[0_2px_6px_rgba(15,23,42,0.02),0_1px_2px_rgba(15,23,42,0.01)]",
        className
      )}
      onClick={onDetailClick}
    >
      {/* Header: Avatar + Name + Meta */}
      <div className="flex items-start gap-3 p-4">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {link.creator.avatar_url ? (
            <img
              src={link.creator.avatar_url}
              alt={creatorName}
              className="w-10 h-10 rounded-full object-cover cursor-pointer"
              onClick={handleUserClick}
            />
          ) : (
            <div 
              className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-sm cursor-pointer"
              onClick={handleUserClick}
            >
              {getInitials(creatorName)}
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
              {creatorName}
            </button>
            {link.creator.primary_role && (
              <>
                <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
                <p className="text-xs font-gilroy font-normal text-muted-foreground">
                  {roleDisplayName(link.creator.primary_role)}
                </p>
              </>
            )}
            {link.linked_location && (
              <>
                <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
                <p className="text-xs font-gilroy font-normal text-muted-foreground truncate">
                  {link.linked_location.name}
                </p>
              </>
            )}
            <span className="text-xs font-gilroy font-normal text-muted-foreground">·</span>
            <p className="text-xs font-gilroy font-normal text-muted-foreground">{timeLabel}</p>
          </div>
          {link.creator.verified && (
            <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-gilroy font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 mt-1">
              Geverifieerd
            </span>
          )}
        </div>

        {(showDelete || isAdmin || isOwner) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              if (isAdmin) {
                handleAdminDelete(e);
              } else {
                onDelete?.();
              }
            }}
            className="text-destructive hover:text-destructive shrink-0"
          >
            <Icon name="Trash2" className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Content Text */}
      <div className="px-4 pb-3">
        {link.post_type === "text" || link.post_type === "media" ? (
          // Text/Media posts: show only description as plain text (Facebook-style)
          link.description && (
            <p className="text-base text-foreground whitespace-pre-wrap leading-relaxed">
              {link.description}
            </p>
          )
        ) : (
          // Link posts: show title and description as before
          <>
            {displayTitle && (
              <h3
                className={cn(
                  "text-lg font-semibold mb-1 line-clamp-2",
                  "cursor-pointer hover:text-primary transition-colors"
                )}
                onClick={handleOpenLink}
              >
                {displayTitle}
              </h3>
            )}
            {link.description && (
              <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                {link.description}
              </p>
            )}
          </>
        )}
        {link.city && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">{link.city}</span>
          </div>
        )}
      </div>

      {/* Media Gallery (for media posts) */}
      {link.post_type === "media" && link.media_urls && link.media_urls.length > 0 && (
        <div className={cn(
          "px-4 pb-4",
          link.media_urls.length === 1 ? "grid grid-cols-1" : 
          link.media_urls.length === 2 ? "grid grid-cols-2 gap-2" :
          "grid grid-cols-2 gap-2"
        )}>
          {link.media_urls.slice(0, 4).map((mediaUrl, index) => {
            const isVideo = mediaUrl.match(/\.(mp4|webm|mov)$/i);
            const showOverlay = link.media_urls.length > 4 && index === 3;
            return (
              <div
                key={index}
                className={cn(
                  "relative overflow-hidden rounded-lg bg-muted",
                  link.media_urls.length === 1 ? "aspect-video max-h-[500px]" : "aspect-square"
                )}
              >
                {isVideo ? (
                  <video
                    src={mediaUrl}
                    className="w-full h-full object-cover cursor-pointer"
                    controls={false}
                    onClick={(e) => handleImageClick(mediaUrl, e)}
                  />
                ) : (
                  <img
                    src={mediaUrl}
                    alt={link.title || `Media ${index + 1}`}
                    className="w-full h-full object-cover cursor-pointer"
                    loading="lazy"
                    onClick={(e) => handleImageClick(mediaUrl, e)}
                    onError={(e) => {
                      // Hide image on error
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                )}
                {showOverlay && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-white font-semibold text-lg pointer-events-none">
                    +{link.media_urls.length - 4}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Preview Image/Video (for link posts) */}
      {link.post_type !== "media" && link.image_url && (
        <div className="relative w-full aspect-video max-h-[400px]">
          <img
            src={link.image_url}
            alt={link.title || "Link preview"}
            className="w-full h-full object-cover cursor-pointer"
            loading="lazy"
            onClick={(e) => {
              e.stopPropagation();
              handleOpenLink(e);
            }}
            onError={(e) => {
              // Hide image on error
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
          {link.video_url && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/20">
              <Icon name="Play" className="h-12 w-12 text-white" />
            </div>
          )}
        </div>
      )}

      {/* Action Row: Emoji Reactions + Report + Bookmark */}
      <div className="flex items-center justify-between gap-4 px-4 py-3 border-t border-border/50">
        {onReactionToggle ? (
          <EmojiReactions
            activityId={link.id}
            reactions={reactionCounts}
            userReaction={userReaction || null}
            onReactionToggle={onReactionToggle}
          />
        ) : (
          <div /> // Spacer
        )}

        <div className="flex items-center gap-2">
          <ReportButton
            reportType="prikbord_post"
            targetId={link.id}
            targetName={link.title || link.url}
            size="sm"
            variant="ghost"
          />
          
          <button
            type="button"
            onClick={handleBookmark}
            disabled={isTogglingBookmark}
            className={cn(
              "flex items-center text-sm transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 rounded",
              "disabled:opacity-50 disabled:cursor-not-allowed",
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

      {/* Image Modal */}
      <ImageModal
        imageUrl={imageModalUrl}
        open={imageModalOpen}
        onOpenChange={setImageModalOpen}
      />
    </div>
  );
}

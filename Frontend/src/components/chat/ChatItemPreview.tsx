// Frontend/src/components/chat/ChatItemPreview.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { PollPreview } from "@/components/feed/PollPreview";
import { Icon } from "@/components/Icon";
import type { ChatTopic } from "@/lib/api";
import { getContentItemPreview, type ContentItemPreview } from "@/lib/api";
import { cn } from "@/lib/ui/cn";
import { navigationActions } from "@/state/navigation";

interface ChatItemPreviewProps {
  topic: ChatTopic;
  className?: string;
}

export function ChatItemPreview({ topic, className }: ChatItemPreviewProps) {
  const navigate = useNavigate();
  const [contentItem, setContentItem] = useState<ContentItemPreview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Don't show preview for general topics
  if (topic.content_type === "general") {
    return null;
  }

  useEffect(() => {
    let isMounted = true;

    const loadContentItem = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const item = await getContentItemPreview(topic.id);
        if (isMounted) {
          setContentItem(item);
        }
      } catch (err: any) {
        // Silently handle 404 or missing content - just don't show preview
        if (err?.status === 404 || err?.message?.includes("not found")) {
          if (isMounted) {
            setError(null);
          }
        } else {
          console.error("Failed to load content item preview:", err);
          if (isMounted) {
            setError(err?.message || "Kon item niet laden");
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadContentItem();

    return () => {
      isMounted = false;
    };
  }, [topic.id]);

  // Don't show loading state - just return null until content is loaded
  if (isLoading || error || !contentItem) {
    return null;
  }

  // For polls, show PollPreview component instead of regular preview
  const isPoll = contentItem.content_type === "feed" &&
    contentItem.activity_type &&
    (contentItem.activity_type === "poll" || contentItem.activity_type === "poll_response") &&
    contentItem.poll_id;

  if (isPoll && contentItem.poll_id) {
    return (
      <div className={cn("px-4 py-3 border-b border-border bg-card", className)}>
        <PollPreview pollId={contentItem.poll_id} hideChatButton={true} />
      </div>
    );
  }

  const handleClick = () => {
    if (contentItem.content_type === "news" || contentItem.content_type === "music") {
      // Open news/music URL in new tab
      if (contentItem.url) {
        window.open(contentItem.url, "_blank", "noopener,noreferrer");
      }
    } else if (contentItem.content_type === "event") {
      // Navigate to events page with detail overlay
      navigationActions.setEvents({ detailId: contentItem.id });
      navigate("/events");
    } else if (contentItem.content_type === "feed") {
      // For check-ins, navigate to location detail page
      // For polls, don't navigate (they show PollPreview component)
      // For other activities, navigate to feed page
      // Don't navigate for polls - they're handled by PollPreview component
      if (isPoll) {
        return; // PollPreview handles interaction
      }
      if (contentItem.activity_type === "check_in" && contentItem.location_id) {
        navigate(`/locations/${contentItem.location_id}`);
      } else {
        navigate("/feed");
      }
    }
  };

  // Make all content types clickable (news, event, feed, music)
  const isClickable = contentItem.content_type === "news" ||
    contentItem.content_type === "event" ||
    contentItem.content_type === "feed" ||
    contentItem.content_type === "music";

  return (
    <div
      className={cn(
        "px-4 py-3 border-b border-border bg-card",
        isClickable && "cursor-pointer hover:bg-muted/50 transition-colors",
        className
      )}
      onClick={isClickable ? handleClick : undefined}
      onKeyDown={(e) => {
        if (isClickable && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          handleClick();
        }
      }}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      aria-label={
        isClickable
          ? `Open ${contentItem.content_type === "news" ? "nieuws" : contentItem.content_type === "event" ? "event" : contentItem.content_type === "music" ? "muziek" : "feed"} item: ${contentItem.title}`
          : undefined
      }
    >
      <div className="flex gap-3 items-start">
        {/* Image */}
        {contentItem.image_url && (
          <div className="flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden border border-border/70 bg-muted">
            <img
              src={contentItem.image_url}
              alt=""
              className="w-full h-full object-cover"
              loading="lazy"
            />
          </div>
        )}
        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Hide icon/label for feed items */}
          {contentItem.content_type !== "feed" && (
            <div className="flex items-center gap-2 mb-1">
              <Icon
                name={
                  contentItem.content_type === "news" || contentItem.content_type === "music"
                    ? "Newspaper"
                    : contentItem.content_type === "event"
                      ? "Calendar"
                      : "Home"
                }
                className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0"
              />
              <span className="text-xs font-gilroy font-semibold text-muted-foreground uppercase">
                {contentItem.content_type === "news"
                  ? "Nieuws"
                  : contentItem.content_type === "music"
                    ? "Muziek"
                    : contentItem.content_type === "event"
                      ? "Event"
                      : "Feed"}
              </span>
            </div>
          )}
          <h3 className="font-gilroy font-semibold text-foreground mb-1 line-clamp-2">
            {contentItem.title}
          </h3>
          {contentItem.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {contentItem.description}
            </p>
          )}
          {/* Only show "Bekijk origineel" for non-poll feed items */}
          {isClickable && contentItem.content_type === "feed" && !isPoll && (
            <div className="mt-2 text-xs text-primary">
              <span>Bekijk origineel</span>
            </div>
          )}
          {isClickable && contentItem.content_type !== "feed" && (
            <div className="mt-2 text-xs text-primary flex items-center gap-1">
              <span>Bekijk origineel</span>
              <Icon name="ExternalLink" className="h-3 w-3" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

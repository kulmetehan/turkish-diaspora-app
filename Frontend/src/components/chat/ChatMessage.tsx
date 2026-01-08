// Frontend/src/components/chat/ChatMessage.tsx
import { useState } from "react";
import { cn } from "@/lib/ui/cn";
import type { ChatMessage as ChatMessageType } from "@/lib/api";
import { QuotePreview } from "./QuotePreview";
import { formatRelativeTime } from "@/lib/utils/date";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { useUserAuth } from "@/hooks/useUserAuth";

interface ChatMessageProps {
  message: ChatMessageType;
  onReply?: (message: ChatMessageType) => void;
  onQuote?: (message: ChatMessageType) => void;
  onEdit?: (message: ChatMessageType) => void;
  onDelete?: (messageId: number) => void;
  onReaction?: (messageId: number, emoji: string) => void;
  onUserClick?: (userId: string) => void;
  className?: string;
}

export function ChatMessage({
  message,
  onReply,
  onQuote,
  onEdit,
  onDelete,
  onReaction,
  onUserClick,
  className,
}: ChatMessageProps) {
  const { userId } = useUserAuth();
  const [showActions, setShowActions] = useState(false);
  const isOwnMessage = message.user_id === userId;

  const handleAvatarClick = () => {
    if (message.user?.id && onUserClick) {
      onUserClick(message.user.id);
    }
  };

  const handleReactionClick = (emoji: string) => {
    onReaction?.(message.id, emoji);
  };

  return (
    <div
      className={cn(
        "flex gap-3 group",
        isOwnMessage ? "flex-row-reverse" : "flex-row",
        className
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <button
          type="button"
          onClick={handleAvatarClick}
          className="w-8 h-8 rounded-full overflow-hidden cursor-pointer hover:ring-2 ring-primary/50 transition-all"
        >
          {message.user?.avatar_url ? (
            <img
              src={message.user.avatar_url}
              alt={message.user.name || ""}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-primary/20 flex items-center justify-center text-primary text-xs font-gilroy font-semibold">
              {(message.user?.name || "?").charAt(0).toUpperCase()}
            </div>
          )}
        </button>
      </div>

      {/* Message Content */}
      <div
        className={cn(
          "flex-1 min-w-0",
          isOwnMessage ? "items-end" : "items-start"
        )}
      >
        {message.user?.name && !isOwnMessage && (
          <div className="text-xs font-gilroy font-semibold mb-1 text-muted-foreground">
            {message.user.name}
          </div>
        )}

        {/* Parent Message (Reply) */}
        {message.parent_message && (
          <div className="mb-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <Icon name="Reply" className="w-3 h-3" />
              <span>Replying to {message.parent_message.user?.name || "unknown"}</span>
            </div>
            <div className="pl-4 border-l-2 border-primary/30">
              <p className="text-xs text-muted-foreground line-clamp-2">
                {message.parent_message.content}
              </p>
            </div>
          </div>
        )}

        {/* Quoted Message */}
        {message.quoted_message && (
          <div className="mb-2">
            <QuotePreview message={message.quoted_message} />
          </div>
        )}

        {/* Message Bubble */}
        <div
          className={cn(
            "inline-block rounded-xl px-3 py-2 max-w-[80%] relative",
            isOwnMessage
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-foreground"
          )}
        >
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
          {message.is_edited && (
            <div className="text-xs opacity-70 mt-1">(bewerkt)</div>
          )}
        </div>

        {/* Reactions */}
        {message.reactions && Object.keys(message.reactions).length > 0 && (
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {Object.entries(message.reactions).map(([emoji, count]) => (
              <button
                key={emoji}
                type="button"
                onClick={() => handleReactionClick(emoji)}
                className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-colors",
                  message.user_reactions?.includes(emoji)
                    ? "bg-primary/20 text-primary border border-primary/30"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted"
                )}
              >
                <span>{emoji}</span>
                <span>{count}</span>
              </button>
            ))}
          </div>
        )}

        {/* Timestamp & Actions */}
        <div className="flex items-center gap-2 mt-1">
          <div className="text-xs text-muted-foreground">
            {formatRelativeTime(message.created_at)}
          </div>
          {showActions && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {onReply && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onReply(message)}
                  className="h-6 px-2 text-xs"
                >
                  <Icon name="Reply" className="w-3 h-3 mr-1" />
                  Reply
                </Button>
              )}
              {onQuote && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onQuote(message)}
                  className="h-6 px-2 text-xs"
                >
                  <Icon name="MessageSquare" className="w-3 h-3 mr-1" />
                  Quote
                </Button>
              )}
              {onReaction && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    // Simple emoji picker - just add 👍
                    handleReactionClick("👍");
                  }}
                  className="h-6 px-2 text-xs"
                >
                  👍
                </Button>
              )}
              {isOwnMessage && onEdit && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(message)}
                  className="h-6 px-2 text-xs"
                >
                  <Icon name="Edit" className="w-3 h-3 mr-1" />
                  Edit
                </Button>
              )}
              {isOwnMessage && onDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(message.id)}
                  className="h-6 px-2 text-xs text-destructive"
                >
                  <Icon name="Trash2" className="w-3 h-3 mr-1" />
                  Delete
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


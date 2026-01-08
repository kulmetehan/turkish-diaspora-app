// Frontend/src/components/chat/ChatButton.tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { getOrCreateChatTopic, getChatTopicByContent } from "@/lib/api";
import { useUserAuth } from "@/hooks/useUserAuth";
import { toast } from "sonner";
import { supabase } from "@/lib/supabaseClient";

interface ChatButtonProps {
  contentType: "feed" | "news" | "event" | "music";
  contentId: number;
  title: string;
  description?: string;
  messageCount?: number; // Optional prop for manual override
  variant?: "default" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  className?: string;
  showCount?: boolean;
}

export function ChatButton({
  contentType,
  contentId,
  title,
  description,
  messageCount: initialMessageCount, // Optional prop for manual override
  variant = "ghost",
  size = "sm",
  className,
  showCount = true,
}: ChatButtonProps) {
  const navigate = useNavigate();
  const { isAuthenticated } = useUserAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [count, setCount] = useState(initialMessageCount ?? 0);
  const [topicId, setTopicId] = useState<number | null>(null);

  // Fetch message count on mount and when content changes
  useEffect(() => {
    if (!isAuthenticated) {
      setCount(0);
      setTopicId(null);
      return;
    }

    let cancelled = false;

    const fetchMessageCount = async () => {
      try {
        const topic = await getChatTopicByContent(contentType, contentId);
        if (!cancelled) {
          if (topic) {
            setCount(topic.message_count);
            setTopicId(topic.id);
          } else {
            setCount(0);
            setTopicId(null);
          }
        }
      } catch (error) {
        console.error("Failed to fetch chat topic:", error);
        if (!cancelled) {
          setCount(0);
          setTopicId(null);
        }
      }
    };

    fetchMessageCount();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, contentType, contentId]);

  // Subscribe to real-time updates for message count when topicId is known
  useEffect(() => {
    if (!topicId || !isAuthenticated) return;

    const channel = supabase
      .channel(`chat-topic-${topicId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "chat_messages",
          filter: `topic_id=eq.${topicId}`,
        },
        async () => {
          // Refetch topic to get updated message_count
          try {
            const topic = await getChatTopicByContent(contentType, contentId);
            if (topic) {
              setCount(topic.message_count);
              setTopicId(topic.id); // Ensure topicId is set
            }
          } catch (error) {
            console.error("Failed to update message count:", error);
          }
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "chat_topics",
          filter: `id=eq.${topicId}`,
        },
        (payload) => {
          // Update count directly from topic update
          if (payload.new?.message_count !== undefined) {
            setCount(payload.new.message_count);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [topicId, isAuthenticated, contentType, contentId]);

  // Periodically check for topic if it doesn't exist yet (polling fallback)
  useEffect(() => {
    if (!isAuthenticated || topicId) return; // Don't poll if we already have a topicId

    const interval = setInterval(async () => {
      try {
        const topic = await getChatTopicByContent(contentType, contentId);
        if (topic) {
          setCount(topic.message_count);
          setTopicId(topic.id);
        }
      } catch (error) {
        // Silently fail - topic might not exist yet
      }
    }, 60000); // Check every 60 seconds (1 minute)

    return () => clearInterval(interval);
  }, [isAuthenticated, topicId, contentType, contentId]);

  // Update count if messageCount prop changes (manual override)
  useEffect(() => {
    if (initialMessageCount !== undefined) {
      setCount(initialMessageCount);
    }
  }, [initialMessageCount]);

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    if (!isAuthenticated) {
      toast.error("Je moet ingelogd zijn om te chatten");
      navigate("/auth", { 
        state: { from: { pathname: window.location.pathname } },
      });
      return;
    }

    setIsLoading(true);
    try {
      const topic = await getOrCreateChatTopic(
        contentType,
        contentId,
        title,
        description
      );
      // Update count and topicId after creating/getting topic
      setCount(topic.message_count);
      setTopicId(topic.id);
      navigate(`/chat/topic/${topic.id}`);
    } catch (error: any) {
      console.error("Failed to get or create chat topic:", error);
      toast.error(error.message || "Kon chat niet openen");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleClick}
      disabled={isLoading}
      className={cn(
        "gap-1.5",
        variant === "ghost" && "text-foreground", // Ensure ghost buttons are visible
        className
      )}
      aria-label={`Open chat voor ${title}${count > 0 ? ` (${count} berichten)` : ""}`}
    >
      <Icon
        name={isLoading ? "Loader2" : "MessageCircle"}
        className={cn("w-4 h-4", isLoading && "animate-spin")}
      />
      {showCount && count > 0 && (
        <span className="text-xs font-semibold">{count}</span>
      )}
    </Button>
  );
}


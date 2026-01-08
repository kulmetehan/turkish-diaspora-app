// Frontend/src/hooks/useChatRealtime.ts
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import type { RealtimeChannel } from "@supabase/supabase-js";
import type { ChatMessage } from "@/lib/api";
import { getChatMessages, getChatMessage } from "@/lib/api";

interface UseChatRealtimeOptions {
  topicId: number | null;
  onMessage?: (message: ChatMessage) => void;
  onUpdate?: (message: ChatMessage) => void;
  onDelete?: (messageId: number) => void;
  enabled?: boolean;
}

interface UseChatRealtimeReturn {
  isConnected: boolean;
  error: Error | null;
}

export function useChatRealtime({
  topicId,
  onMessage,
  onUpdate,
  onDelete,
  enabled = true,
}: UseChatRealtimeOptions): UseChatRealtimeReturn {
  const channelRef = useRef<RealtimeChannel | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const onMessageRef = useRef(onMessage);
  const onUpdateRef = useRef(onUpdate);
  const onDeleteRef = useRef(onDelete);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onUpdateRef.current = onUpdate;
    onDeleteRef.current = onDelete;
  }, [onMessage, onUpdate, onDelete]);

  useEffect(() => {
    if (!topicId || !enabled) {
      return;
    }

    // Cleanup existing subscription
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current);
      channelRef.current = null;
      setIsConnected(false);
    }

    // Create channel for this topic
    const channelName = `chat:topic:${topicId}`;
    const channel = supabase
      .channel(channelName, {
        config: {
          broadcast: { self: true },
          presence: { key: "user" },
        },
      })
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "chat_messages",
          filter: `topic_id=eq.${topicId}`,
        },
        async (payload) => {
          // Notify parent component - fetch full message details using message ID
          const messageId = (payload.new as any)?.id;
          if (messageId && onMessageRef.current) {
            try {
              // Fetch the specific message with full user data
              const newMessage = await getChatMessage(messageId);
              onMessageRef.current?.(newMessage);
            } catch (err) {
              console.error("Failed to fetch new message:", err);
              // Fallback: try to get from message list
              try {
                const response = await getChatMessages(topicId, 50);
                if (response.items) {
                  const foundMessage = response.items.find((msg) => msg.id === messageId);
                  if (foundMessage) {
                    onMessageRef.current?.(foundMessage);
                  }
                }
              } catch (fallbackErr) {
                console.error("Fallback fetch also failed:", fallbackErr);
              }
            }
          }
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "chat_messages",
          filter: `topic_id=eq.${topicId}`,
        },
        async (payload) => {
          // Notify parent component - fetch updated message details using message ID
          const messageId = (payload.new as any)?.id;
          if (messageId && onUpdateRef.current) {
            try {
              // Fetch the specific updated message with full user data
              const updatedMessage = await getChatMessage(messageId);
              onUpdateRef.current?.(updatedMessage);
            } catch (err) {
              console.error("Failed to fetch updated message:", err);
            }
          }
        }
      )
      .on(
        "postgres_changes",
        {
          event: "DELETE",
          schema: "public",
          table: "chat_messages",
          filter: `topic_id=eq.${topicId}`,
        },
        (payload) => {
          const messageId = (payload.old as any)?.id;
          if (messageId) {
            onDeleteRef.current?.(messageId);
          }
        }
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") {
          setIsConnected(true);
          setError(null);
        } else if (status === "CHANNEL_ERROR") {
          setError(new Error("Failed to subscribe to chat channel"));
          setIsConnected(false);
        } else if (status === "TIMED_OUT") {
          setError(new Error("Chat subscription timed out"));
          setIsConnected(false);
        } else if (status === "CLOSED") {
          setIsConnected(false);
        }
      });

    channelRef.current = channel;

    // Cleanup on unmount or when topicId changes
    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
        setIsConnected(false);
      }
    };
  }, [topicId, enabled]);

  return {
    isConnected,
    error,
  };
}


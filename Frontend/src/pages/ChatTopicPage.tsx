// Frontend/src/pages/ChatTopicPage.tsx
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ChatItemPreview } from "@/components/chat/ChatItemPreview";
import { ChatMessage as ChatMessageComponent } from "@/components/chat/ChatMessage";
import { QuotePreview } from "@/components/chat/QuotePreview";
import { AppHeader } from "@/components/feed/AppHeader";
import { Icon } from "@/components/Icon";
import { AppViewportShell } from "@/components/layout";
import { UserProfileOverlay } from "@/components/profile/UserProfileOverlay";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EmojiPicker } from "@/components/ui/EmojiPicker";
import { Textarea } from "@/components/ui/textarea";
import { useChatRealtime } from "@/hooks/useChatRealtime";
import { useTranslation } from "@/hooks/useTranslation";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
  createChatMessage,
  deleteChatMessage,
  editChatMessage,
  getChatMessages,
  getChatTopic,
  toggleChatReaction,
  type ChatMessage,
  type ChatTopic,
} from "@/lib/api";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import { toast } from "sonner";

export default function ChatTopicPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const topicId = id ? parseInt(id, 10) : null;
  const { isAuthenticated, isLoading: authLoading, userId } = useUserAuth();
  const seo = useSeo({ title: "Chat Topic" });

  const [topic, setTopic] = useState<ChatTopic | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingTopic, setIsLoadingTopic] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messageContent, setMessageContent] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const prevMessagesLengthRef = useRef(0);

  // Reply/Quote state
  const [replyingTo, setReplyingTo] = useState<ChatMessage | null>(null);
  const [quoting, setQuoting] = useState<ChatMessage | null>(null);

  // Edit state
  const [editingMessage, setEditingMessage] = useState<ChatMessage | null>(null);
  const [editContent, setEditContent] = useState("");
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Profile overlay state
  const [profileOverlayUserId, setProfileOverlayUserId] = useState<string | null>(null);

  // Real-time subscription
  const { isConnected, error: realtimeError } = useChatRealtime({
    topicId,
    enabled: isAuthenticated && !authLoading && !!topicId,
    onMessage: (message: ChatMessage) => {
      // Add new message to list if not already present
      setMessages((prev) => {
        // Check if message already exists
        if (prev.some((m) => m.id === message.id)) {
          return prev;
        }
        // Replace optimistic message (negative ID) with real message if content matches
        // This handles the case where real-time update comes after optimistic update
        const optimisticIndex = prev.findIndex((m) =>
          m.id < 0 &&
          m.content === message.content &&
          m.user_id === message.user_id
        );
        if (optimisticIndex >= 0) {
          // Replace optimistic message with real one
          const newMessages = [...prev];
          newMessages[optimisticIndex] = message;
          return newMessages;
        }
        // Add new message
        return [...prev, message];
      });
    },
    onUpdate: (message: ChatMessage) => {
      // Update existing message
      setMessages((prev) =>
        prev.map((m) => (m.id === message.id ? message : m))
      );
    },
    onDelete: (messageId: number) => {
      // Remove deleted message
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
    },
  });

  // Redirect to login if not authenticated
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      navigate("/auth", {
        state: { from: { pathname: `/chat/topic/${topicId}` } },
        replace: true
      });
    }
  }, [isAuthenticated, authLoading, navigate, topicId]);

  // Validate topic ID
  useEffect(() => {
    if (!topicId || isNaN(topicId)) {
      navigate("/chat", { replace: true });
    }
  }, [topicId, navigate]);

  // Load topic
  useEffect(() => {
    if (!topicId || !isAuthenticated || authLoading) return;

    const loadTopic = async () => {
      setIsLoadingTopic(true);
      try {
        const topicData = await getChatTopic(topicId);
        setTopic(topicData);
      } catch (err: any) {
        console.error("Failed to load topic:", err);
        setError(err.message || "Kon topic niet laden");
        toast.error("Kon topic niet laden");
      } finally {
        setIsLoadingTopic(false);
      }
    };

    loadTopic();
  }, [topicId, isAuthenticated, authLoading]);

  // Load messages
  useEffect(() => {
    if (!topicId || !isAuthenticated || authLoading) return;

    const loadMessages = async () => {
      setIsLoadingMessages(true);
      try {
        const response = await getChatMessages(topicId);
        setMessages(response.items);
        setHasMore(response.has_more);
      } catch (err: any) {
        console.error("Failed to load messages:", err);
        setError(err.message || "Kon messages niet laden");
        toast.error("Kon messages niet laden");
      } finally {
        setIsLoadingMessages(false);
      }
    };

    loadMessages();
  }, [topicId, isAuthenticated, authLoading]);

  // Track scroll position
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setIsAtBottom(isNearBottom);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Scroll to bottom when new messages arrive (only if already at bottom)
  useEffect(() => {
    const prevLength = prevMessagesLengthRef.current;
    const currentLength = messages.length;
    prevMessagesLengthRef.current = currentLength;

    // Only auto-scroll if user was already at bottom or if it's the first load
    if (isAtBottom || prevLength === 0) {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: prevLength === 0 ? "auto" : "smooth" });
      }
    }
  }, [messages, isAtBottom]);

  const handleSendMessage = async () => {
    if (!topicId || !messageContent.trim() || isSending) return;

    setIsSending(true);
    const contentToSend = messageContent.trim();

    // Create optimistic message with temporary negative ID
    const tempId = -Date.now();
    const optimisticMessage: ChatMessage = {
      id: tempId,
      topic_id: topicId,
      user_id: userId || "",
      content: contentToSend,
      parent_message_id: replyingTo?.id || null,
      quoted_message_id: quoting?.id || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_edited: false,
      is_deleted: false,
      user: userId ? { id: userId } : null,
      parent_message: replyingTo || null,
      quoted_message: quoting || null,
    };

    // Add optimistic message immediately
    setMessages((prev) => [...prev, optimisticMessage]);
    setMessageContent("");
    const savedReplyingTo = replyingTo;
    const savedQuoting = quoting;
    setReplyingTo(null);
    setQuoting(null);

    try {
      await createChatMessage(topicId, {
        content: contentToSend,
        parent_message_id: savedReplyingTo?.id || null,
        quoted_message_id: savedQuoting?.id || null,
      });

      // Set up fallback: if optimistic message still exists after 2 seconds, refresh
      const fallbackTimeout = setTimeout(async () => {
        setMessages((prev) => {
          // Check if optimistic message still exists (has negative ID)
          const stillHasOptimistic = prev.some((m) => m.id === tempId);
          if (stillHasOptimistic) {
            // Fallback: refresh messages manually
            getChatMessages(topicId).then((response) => {
              setMessages(response.items);
            }).catch((err) => {
              console.error("Fallback refresh failed:", err);
            });
          }
          return prev;
        });
      }, 2000);

      // Clean up timeout if component unmounts or message is replaced
      // The real-time hook will replace the optimistic message, so we can clear timeout then
      setTimeout(() => clearTimeout(fallbackTimeout), 3000);

      // Reload topic to update message count
      if (topic) {
        const updatedTopic = await getChatTopic(topicId);
        setTopic(updatedTopic);
      }
    } catch (err: any) {
      console.error("Failed to send message:", err);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      // Restore input and reply state
      setMessageContent(contentToSend);
      setReplyingTo(savedReplyingTo);
      setQuoting(savedQuoting);
      toast.error(err.message || "Kon bericht niet versturen");
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleReply = (message: ChatMessage) => {
    setReplyingTo(message);
    setQuoting(null);
    // Scroll to input
    setTimeout(() => {
      const input = document.querySelector('textarea[placeholder*="bericht"]') as HTMLTextAreaElement;
      input?.focus();
    }, 100);
  };

  const handleQuote = (message: ChatMessage) => {
    setQuoting(message);
    setReplyingTo(null);
    // Scroll to input
    setTimeout(() => {
      const input = document.querySelector('textarea[placeholder*="bericht"]') as HTMLTextAreaElement;
      input?.focus();
    }, 100);
  };

  const handleEdit = (message: ChatMessage) => {
    setEditingMessage(message);
    setEditContent(message.content);
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingMessage || !editContent.trim() || isSavingEdit) return;

    setIsSavingEdit(true);
    try {
      const updated = await editChatMessage(editingMessage.id, {
        content: editContent.trim(),
      });

      // Update message in list
      setMessages((prev) =>
        prev.map((m) => (m.id === updated.id ? updated : m))
      );

      setIsEditModalOpen(false);
      setEditingMessage(null);
      setEditContent("");
      toast.success("Bericht bewerkt");
    } catch (err: any) {
      console.error("Failed to edit message:", err);
      toast.error(err.message || "Kon bericht niet bewerken");
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDelete = async (messageId: number) => {
    if (!confirm("Weet je zeker dat je dit bericht wilt verwijderen?")) {
      return;
    }

    try {
      await deleteChatMessage(messageId);

      // Remove message from list
      setMessages((prev) => prev.filter((m) => m.id !== messageId));

      toast.success("Bericht verwijderd");
    } catch (err: any) {
      console.error("Failed to delete message:", err);
      toast.error(err.message || "Kon bericht niet verwijderen");
    }
  };

  const handleUserClick = useCallback((userId: string) => {
    setProfileOverlayUserId(userId);
  }, []);

  const handleReaction = async (messageId: number, emoji: string) => {
    try {
      const response = await toggleChatReaction(messageId, emoji);

      // Update message reactions - need to determine user reactions from API response
      // For now, just update reactions. The backend should return user_reactions in the full message.
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
              ...m,
              reactions: response.reactions,
            }
            : m
        )
      );

      // Reload message to get updated user_reactions
      const updatedMessages = await getChatMessages(topicId!, 50);
      const updatedMessage = updatedMessages.items.find((m) => m.id === messageId);
      if (updatedMessage) {
        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? updatedMessage : m))
        );
      }
    } catch (err: any) {
      console.error("Failed to toggle reaction:", err);
      toast.error(err.message || "Kon reactie niet toevoegen");
    }
  };

  if (authLoading || !isAuthenticated || !topicId) {
    return (
      <AppViewportShell>
        <SeoHead {...seo} />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-muted-foreground">Laden...</div>
        </div>
      </AppViewportShell>
    );
  }

  if (isLoadingTopic) {
    return (
      <AppViewportShell>
        <SeoHead {...seo} />
        <AppHeader />
        <div className="flex items-center justify-center flex-1 text-muted-foreground">
          Laden...
        </div>
      </AppViewportShell>
    );
  }

  if (error || !topic) {
    return (
      <AppViewportShell>
        <SeoHead {...seo} />
        <AppHeader />
        <div className="flex items-center justify-center flex-1">
          <div className="text-center">
            <p className="text-destructive mb-4">{error || "Topic niet gevonden"}</p>
            <Button onClick={() => navigate("/chat")}>Terug naar Chat</Button>
          </div>
        </div>
      </AppViewportShell>
    );
  }

  return (
    <AppViewportShell>
      <SeoHead {...seo} />
      <div className="flex flex-col h-full relative">
        {/* Red gradient overlay */}
        <div
          className="absolute inset-x-0 top-0 pointer-events-none z-0"
          style={{
            height: '25%',
            background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
          }}
        />
        <AppHeader />
        <div className="flex flex-col flex-1 overflow-hidden relative z-10">
          {/* Topic Header - Sticky */}
          {/* Hide full header for news items, only show back button */}
          {topic.content_type === "news" ? (
            <div className="sticky top-0 z-20 px-4 py-3 border-b border-border bg-card/95 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/chat")}
                  className="-ml-2"
                >
                  <Icon name="ArrowLeft" className="w-4 h-4 mr-2" />
                  Terug
                </Button>
              </div>
            </div>
          ) : (
            <div className="sticky top-0 z-20 px-4 py-3 border-b border-border bg-card/95 backdrop-blur-sm">
              <div className="max-w-3xl mx-auto">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/chat")}
                  className="mb-2 -ml-2"
                >
                  <Icon name="ArrowLeft" className="w-4 h-4 mr-2" />
                  Terug
                </Button>
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-lg font-gilroy font-semibold">{topic.title}</h1>
                    {topic.description && topic.content_type === "general" && (
                      <p className="text-sm text-muted-foreground mt-1">{topic.description}</p>
                    )}
                  </div>
                  {isAuthenticated && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {isConnected ? (
                        <>
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                          <span>Live</span>
                        </>
                      ) : (
                        <>
                          <div className="w-2 h-2 rounded-full bg-gray-400" />
                          <span>Offline</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Content Item Preview */}
          {topic && <ChatItemPreview key={topic.id} topic={topic} />}

          {/* Messages List */}
          <div
            ref={messagesContainerRef}
            className="flex-1 overflow-y-auto px-4 py-4"
          >
            <div className="max-w-3xl mx-auto space-y-4">
              {isLoadingMessages ? (
                <div className="text-center py-8 text-muted-foreground">Laden...</div>
              ) : messages.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Nog geen berichten. Start het gesprek!
                </div>
              ) : (
                messages.map((message) => (
                  <ChatMessageComponent
                    key={message.id}
                    message={message}
                    onReply={handleReply}
                    onQuote={handleQuote}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onReaction={handleReaction}
                    onUserClick={handleUserClick}
                  />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Message Input */}
          <div className="px-4 py-3 border-t border-border bg-card">
            <div className="max-w-3xl mx-auto space-y-2">
              {/* Reply/Quote Preview */}
              {replyingTo && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50 border border-border">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <Icon name="Reply" className="w-4 h-4 text-primary flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-gilroy font-semibold text-muted-foreground">
                        Replying to {replyingTo.user?.name || "unknown"}
                      </div>
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {replyingTo.content}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setReplyingTo(null)}
                    className="flex-shrink-0"
                  >
                    <Icon name="X" className="w-4 h-4" />
                  </Button>
                </div>
              )}
              {quoting && (
                <div className="flex items-start justify-between gap-2">
                  <QuotePreview message={quoting} onClose={() => setQuoting(null)} className="flex-1" />
                </div>
              )}

              {/* Input */}
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Textarea
                    value={messageContent}
                    onChange={(e) => setMessageContent(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={
                      replyingTo ? "Type je reply..." : quoting ? "Type je quote reply..." : "Typ een bericht..."
                    }
                    className="flex-1 min-h-[60px] resize-none pr-10"
                    disabled={isSending}
                  />
                  <div className="absolute bottom-2 right-2">
                    <EmojiPicker
                      onEmojiSelect={(emoji) => {
                        setMessageContent((prev) => prev + emoji);
                      }}
                      trigger={
                        <button
                          type="button"
                          className="p-1 rounded hover:bg-muted transition-colors"
                          aria-label="Voeg emoji toe"
                        >
                          <Icon name="Smile" className="w-4 h-4 text-muted-foreground" />
                        </button>
                      }
                    />
                  </div>
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!messageContent.trim() || isSending}
                  className="self-end"
                >
                  {isSending ? (
                    <Icon name="Loader2" className="w-4 h-4 animate-spin" />
                  ) : (
                    <Icon name="Send" className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Edit Dialog */}
          <Dialog open={isEditModalOpen && !!editingMessage} onOpenChange={(open) => {
            if (!open) {
              setIsEditModalOpen(false);
              setEditingMessage(null);
              setEditContent("");
            }
          }}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Bericht bewerken</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  placeholder="Bewerk je bericht..."
                  className="min-h-[100px] resize-none"
                  disabled={isSavingEdit}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsEditModalOpen(false);
                      setEditingMessage(null);
                      setEditContent("");
                    }}
                    disabled={isSavingEdit}
                  >
                    Annuleren
                  </Button>
                  <Button
                    onClick={handleSaveEdit}
                    disabled={!editContent.trim() || isSavingEdit}
                  >
                    Opslaan
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Profile Overlay */}
          {profileOverlayUserId && (
            <UserProfileOverlay
              userId={profileOverlayUserId}
              open={true}
              onClose={() => setProfileOverlayUserId(null)}
              onUserClick={(clickedUserId) => {
                // If clicking on a different user, close current overlay and open new one
                if (clickedUserId !== profileOverlayUserId) {
                  setProfileOverlayUserId(clickedUserId);
                }
              }}
            />
          )}
        </div>
      </div>
    </AppViewportShell>
  );
}


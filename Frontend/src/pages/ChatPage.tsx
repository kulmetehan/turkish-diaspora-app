// Frontend/src/pages/ChatPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AppHeader } from "@/components/feed/AppHeader";
import { LoginPrompt } from "@/components/auth/LoginPrompt";
import { LoginModal } from "@/components/auth/LoginModal";
import { Icon } from "@/components/Icon";
import { AppViewportShell } from "@/components/layout";
import { useTranslation } from "@/hooks/useTranslation";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
  listChatTopics,
  type ChatTopic,
} from "@/lib/api";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import { cn } from "@/lib/ui/cn";
import { toast } from "sonner";

function translateContentType(contentType: string): string {
  const translations: Record<string, string> = {
    news: "Nieuws",
    event: "Events",
    feed: "Feed",
    music: "Muziek",
  };
  return translations[contentType] || contentType;
}

function getContentTypeIcon(contentType: string): string {
  const iconMap: Record<string, string> = {
    general: "Moon",
    news: "Newspaper",
    event: "Calendar",
    feed: "Home",
    music: "Music",
  };
  return iconMap[contentType] || "Tag";
}

function formatShortRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "zojuist";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} min. geleden`;
  } else if (diffHours < 24) {
    return `${diffHours} uur geleden`;
  } else if (diffDays === 1) {
    return "gisteren";
  } else if (diffDays < 7) {
    return `${diffDays} dagen geleden`;
  } else {
    return `${diffDays} dagen geleden`;
  }
}

export default function ChatPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading } = useUserAuth();
  const seo = useSeo({ title: "Chat" });

  const [topics, setTopics] = useState<ChatTopic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contentTypeFilter, setContentTypeFilter] = useState<string | undefined>("general"); // Default to Turkchat
  const [loginModalOpen, setLoginModalOpen] = useState(false);

  // Load topics
  useEffect(() => {
    if (!isAuthenticated || authLoading) return;

    const loadTopics = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // If contentTypeFilter is undefined (showing all), fetch all types and combine
        // Otherwise, filter by the selected type
        if (contentTypeFilter === undefined) {
          // Fetch all non-general topics (combine news, event, feed, music)
          // For "Alle" (undefined), fetch all non-general topics
          const allPromises = [
            listChatTopics("news", 50, 0),
            listChatTopics("event", 50, 0),
            listChatTopics("feed", 50, 0),
            listChatTopics("music", 50, 0),
          ];
          const allResponses = await Promise.all(allPromises);
          const allTopics = allResponses.flatMap((res) => res.items);
          // Sort: pinned first, then updated_at DESC
          allTopics.sort((a, b) => {
            if (a.is_pinned && !b.is_pinned) return -1;
            if (!a.is_pinned && b.is_pinned) return 1;
            if (a.is_pinned && b.is_pinned && a.pinned_at && b.pinned_at) {
              return new Date(b.pinned_at).getTime() - new Date(a.pinned_at).getTime();
            }
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
          });
          setTopics(allTopics);
        } else {
          const response = await listChatTopics(contentTypeFilter, 50, 0);
          // Topics are already sorted by backend (pinned first), but ensure client-side sort too
          const sortedTopics = [...response.items].sort((a, b) => {
            if (a.is_pinned && !b.is_pinned) return -1;
            if (!a.is_pinned && b.is_pinned) return 1;
            if (a.is_pinned && b.is_pinned && a.pinned_at && b.pinned_at) {
              return new Date(b.pinned_at).getTime() - new Date(a.pinned_at).getTime();
            }
            return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
          });
          setTopics(sortedTopics);
        }
      } catch (err: any) {
        console.error("Failed to load chat topics:", err);
        setError(err.message || "Kon chat topics niet laden");
        toast.error("Kon chat topics niet laden");
      } finally {
        setIsLoading(false);
      }
    };

    loadTopics();
  }, [isAuthenticated, authLoading, contentTypeFilter]);

  const handleTopicClick = (topicId: number) => {
    navigate(`/chat/topic/${topicId}`);
  };

  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
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
          <div className="flex-1 overflow-y-auto px-4 pb-24 relative z-10">
        <div className="max-w-3xl mx-auto py-4">
          <h1 className="text-2xl font-gilroy font-black px-4 py-1.5 mb-4">Praat nu mee...</h1>

          {/* Show login prompt if not authenticated */}
          {!isAuthenticated && !authLoading && (
            <div className="px-4 mb-4">
              <LoginPrompt 
                message="Log in om te chatten" 
                onLoginClick={() => setLoginModalOpen(true)}
              />
            </div>
          )}

          {/* Filters - only show when authenticated */}
          {isAuthenticated && (
          <div
            className="flex gap-2 mb-4 overflow-x-auto px-4 py-2"
            style={{
              scrollbarWidth: "none", // Firefox
              msOverflowStyle: "none", // IE/Edge
            }}
          >
            <button
              type="button"
              onClick={() => setContentTypeFilter("general")}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === "general"
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === "general"}
            >
              <Icon name="Moon" className="h-4 w-4" />
              Turkchat
            </button>
            <button
              type="button"
              onClick={() => setContentTypeFilter("feed")}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === "feed"
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === "feed"}
            >
              <Icon name="Home" className="h-4 w-4" />
              Feed
            </button>
            <button
              type="button"
              onClick={() => setContentTypeFilter("news")}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === "news"
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === "news"}
            >
              <Icon name="Newspaper" className="h-4 w-4" />
              Nieuws
            </button>
            <button
              type="button"
              onClick={() => setContentTypeFilter("event")}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === "event"
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === "event"}
            >
              <Icon name="Calendar" className="h-4 w-4" />
              Events
            </button>
            <button
              type="button"
              onClick={() => setContentTypeFilter("music")}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === "music"
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === "music"}
            >
              <Icon name="Music" className="h-4 w-4" />
              Muziek
            </button>
          </div>
          )}

          {/* Topics List - only show when authenticated */}
          {isAuthenticated && (
          <>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Laden...</div>
          ) : error ? (
            <div className="text-center py-8 text-destructive">{error}</div>
          ) : topics.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Geen chat topics gevonden.
            </div>
          ) : (
            <div className="space-y-3">
              {topics.map((topic) => (
                <div
                  key={topic.id}
                  onClick={() => handleTopicClick(topic.id)}
                  className="p-4 rounded-xl border border-border/50 bg-card cursor-pointer hover:border-border hover:shadow-soft transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3 items-start flex-1 min-w-0">
                      {/* Image */}
                      {topic.image_url && (
                        <div className="flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden border border-border/70 bg-muted">
                          <img
                            src={topic.image_url}
                            alt={topic.title}
                            className="w-full h-full object-cover"
                            loading="lazy"
                          />
                        </div>
                      )}
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-gilroy font-semibold text-foreground line-clamp-1">
                            {topic.title}
                          </h3>
                          {topic.is_pinned && (
                            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-primary/10 text-primary text-xs font-gilroy font-medium">
                              <Icon name="Pin" className="h-3 w-3" />
                              <span>Vastgezet</span>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                          <Icon name={getContentTypeIcon(topic.content_type) as any} className="h-3.5 w-3.5 flex-shrink-0" />
                          <Icon name="MessageSquare" className="h-3.5 w-3.5 flex-shrink-0" />
                          <span>{topic.message_count}</span>
                          {topic.topic_category && (
                            <>
                              <span>•</span>
                              <span className="capitalize">{topic.topic_category}</span>
                            </>
                          )}
                          {topic.last_message_at && (
                            <>
                              <span>•</span>
                              <span>
                                Laatste: {formatShortRelativeTime(topic.last_message_at)}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <Icon
                      name="ChevronRight"
                      className="w-5 h-5 text-muted-foreground flex-shrink-0"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
          </>
          )}
        </div>
      </div>
        </div>
      </AppViewportShell>
      {/* Login modal for email/password login */}
      <LoginModal
        open={loginModalOpen}
        onOpenChange={setLoginModalOpen}
      />
    </>
  );
}


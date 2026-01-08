// Frontend/src/pages/ChatPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AppHeader } from "@/components/feed/AppHeader";
import { AppViewportShell } from "@/components/layout";
import { useTranslation } from "@/hooks/useTranslation";
import { useUserAuth } from "@/hooks/useUserAuth";
import {
  listChatTopics,
  type ChatTopic,
} from "@/lib/api";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import { toast } from "sonner";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { formatRelativeTime } from "@/lib/utils/date";

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
  const [contentTypeFilter, setContentTypeFilter] = useState<string | undefined>(undefined);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      navigate("/auth", { 
        state: { from: { pathname: "/chat" } },
        replace: true 
      });
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Load topics
  useEffect(() => {
    if (!isAuthenticated || authLoading) return;

    const loadTopics = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await listChatTopics(contentTypeFilter, 50, 0);
        setTopics(response.items);
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

  if (authLoading || !isAuthenticated) {
    return (
      <AppViewportShell>
        <SeoHead {...seo} />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-muted-foreground">Laden...</div>
        </div>
      </AppViewportShell>
    );
  }

  return (
    <AppViewportShell>
      <SeoHead {...seo} />
      <AppHeader />
      <div className="flex-1 overflow-y-auto px-4 pb-24">
        <div className="max-w-3xl mx-auto py-4">
          <h1 className="text-2xl font-gilroy font-black px-4 py-1.5 mb-4">Praat nu mee...</h1>

          {/* Filters */}
          <div 
            className="flex gap-2 mb-4 overflow-x-auto px-4 py-2"
            style={{
              scrollbarWidth: "none", // Firefox
              msOverflowStyle: "none", // IE/Edge
            }}
          >
            <button
              type="button"
              onClick={() => setContentTypeFilter(undefined)}
              className={cn(
                "flex-shrink-0 flex items-center gap-2 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
                contentTypeFilter === undefined
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "bg-gray-100 text-black hover:bg-gray-200"
              )}
              aria-pressed={contentTypeFilter === undefined}
            >
              Alle
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

          {/* Topics List */}
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
                        <h3 className="font-gilroy font-semibold text-foreground mb-2 line-clamp-1">
                          {topic.title}
                        </h3>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Icon name={getContentTypeIcon(topic.content_type) as any} className="h-3.5 w-3.5 flex-shrink-0" />
                          <Icon name="MessageSquare" className="h-3.5 w-3.5 flex-shrink-0" />
                          <span>{topic.message_count}</span>
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
        </div>
      </div>
    </AppViewportShell>
  );
}


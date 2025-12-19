import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import type { EventItem } from "@/api/events";
import { Icon } from "@/components/Icon";
import { ReportButton } from "@/components/report/ReportButton";
import { ShareButton } from "@/components/share/ShareButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmojiPicker } from "@/components/ui/EmojiPicker";
import { getEventReactions, toggleEventReaction, type ReactionStats, type ReactionType } from "@/lib/api";
import { cn } from "@/lib/ui/cn";

import { formatCityLabel, formatEventDateRange } from "./eventFormatters";

type EventDetailOverlayProps = {
  event: EventItem | null;
  onBackToList: () => void;
};

const DESCRIPTION_THRESHOLD = 160;

// No longer using fixed reaction types - reactions are now custom emoji strings


export function EventDetailOverlay({ event, onBackToList }: EventDetailOverlayProps) {
  if (!event) return null;

  const eventId = event.id;

  const dateLabel = useMemo(() => {
    return formatEventDateRange(event.start_time_utc, event.end_time_utc);
  }, [event]);

  const description = event?.description?.trim() ?? "";
  const summary = event?.summary_ai?.trim() ?? "";
  const hasDescription = description.length > 0;
  const shouldShowSummary = summary.length > 0 && description.length < DESCRIPTION_THRESHOLD;

  // State for reactions
  const [reactionStats, setReactionStats] = useState<ReactionStats | null>(null);
  const [userReaction, setUserReaction] = useState<ReactionType | null>(null);
  const [reactionLoading, setReactionLoading] = useState<ReactionType | null>(null);

  // State for loading initial data
  const [initialLoading, setInitialLoading] = useState(true);

  // Load initial data when component mounts
  useEffect(() => {
    const loadData = async () => {
      setInitialLoading(true);
      try {
        // Load reaction stats
        const reactionData = await getEventReactions(eventId);
        setReactionStats({
          location_id: eventId, // Using eventId as location_id for ReactionStats type compatibility
          reactions: reactionData.reactions,
        });
        // Set user reaction from API response
        setUserReaction(reactionData.user_reaction || null);
      } catch (error: any) {
        console.error("Failed to load event data:", error);
        // Don't show toast here to avoid spam
      } finally {
        setInitialLoading(false);
      }
    };

    loadData();
  }, [eventId]);

  // Reaction handler
  const handleReaction = async (reactionType: ReactionType) => {
    if (reactionLoading) return;

    const hasReaction = userReaction === reactionType;
    setReactionLoading(reactionType);

    try {
      // Toggle reaction (add if not exists, remove if exists)
      const result = await toggleEventReaction(eventId, reactionType);

      // Update user reaction based on result
      setUserReaction(result.is_active ? reactionType : null);

      // Refresh stats
      const stats = await getEventReactions(eventId);
      setReactionStats({
        location_id: eventId,
        reactions: stats.reactions,
      });
      setUserReaction(stats.user_reaction || null);
    } catch (error: any) {
      toast.error(error.message || "Fout bij bijwerken van reaction");
    } finally {
      setReactionLoading(null);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header with back button */}
      <div className="flex items-center gap-3 p-4 border-b bg-background flex-shrink-0">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onBackToList();
          }}
          className="flex items-center gap-2"
        >
          <Icon name="ArrowLeft" className="h-4 w-4" />
          Back to List
        </Button>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <ReportButton
            reportType="location"
            targetId={eventId}
            targetName={event.title}
            size="sm"
          />
        </div>
      </div>

      {/* Event content */}
      <div className="flex-1 p-4">
        {/* Event Info Card - All content in one card */}
        <Card className="p-4 mb-4">
          <div className="space-y-4">
            {/* Title and Date */}
            <div>
              <h2 className="text-xl font-semibold">{event.title}</h2>
              <p className="mt-1 text-sm text-foreground/70">{dateLabel}</p>
            </div>

            {/* City tag with share button */}
            {event.city_key && (
              <div className="flex items-center gap-2">
                <Badge className="bg-primary text-primary-foreground">
                  <Icon name="MapPin" className="mr-1 h-3.5 w-3.5" aria-hidden />
                  {formatCityLabel(event.city_key)}
                </Badge>
                <ShareButton
                  event={{
                    id: eventId,
                    title: event.title,
                  }}
                  size="sm"
                  className="bg-green-600 hover:bg-green-700 text-white border-green-600 hover:border-green-700"
                />
              </div>
            )}

            {/* Location */}
            {event.location_text && (
              <div className="flex items-start gap-3 pt-2 border-t">
                <Icon name="MapPin" className="mt-0.5 h-4 w-4 text-foreground/70" />
                <div>
                  <p className="text-sm font-medium text-foreground/70">Locatie</p>
                  <p className="mt-1 text-sm leading-snug">{event.location_text}</p>
                </div>
              </div>
            )}

            {/* Description */}
            {hasDescription && (
              <div className="flex items-start gap-3 pt-2 border-t">
                <Icon name="AlignLeft" className="mt-0.5 h-4 w-4 text-foreground/70" />
                <div>
                  <p className="text-sm font-medium text-foreground/70">Beschrijving</p>
                  <p className="mt-1 whitespace-pre-line text-sm leading-snug">{description}</p>
                </div>
              </div>
            )}

            {/* AI Summary */}
            {shouldShowSummary && (
              <div className="flex items-start gap-3 pt-2 border-t">
                <Icon name="Sparkles" className="mt-0.5 h-4 w-4 text-foreground/70" />
                <div>
                  <p className="text-sm font-medium text-foreground/70">AI-samenvatting</p>
                  <p className="mt-1 whitespace-pre-line text-sm leading-snug">{summary}</p>
                </div>
              </div>
            )}

            {initialLoading ? (
              <div className="pt-4 border-t">
                <div className="text-center text-sm text-foreground/70">Laden...</div>
              </div>
            ) : (
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-foreground/70">Reactions</h4>
                  <EmojiPicker
                    onEmojiSelect={handleReaction}
                  />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {reactionStats?.reactions && Object.entries(reactionStats.reactions).map(([emoji, count]) => {
                    if (count === 0) return null;
                    const isActive = userReaction === emoji;
                    const isLoading = reactionLoading === emoji;

                    return (
                      <button
                        key={emoji}
                        type="button"
                        onClick={() => handleReaction(emoji)}
                        disabled={isLoading}
                        className={cn(
                          "flex items-center gap-1 px-2 py-1.5 rounded-lg transition-all",
                          "hover:bg-muted focus:outline-none focus:ring-2 focus:ring-primary/30",
                          "disabled:opacity-50 disabled:cursor-not-allowed",
                          isActive
                            ? "bg-primary/10 text-primary border border-primary/30 scale-110"
                            : "bg-transparent"
                        )}
                        aria-label={`${emoji} reaction`}
                        title={emoji}
                      >
                        <span className="text-lg leading-none">{emoji}</span>
                        {count > 0 && (
                          <span
                            className={cn(
                              "text-xs font-gilroy font-medium",
                              isActive ? "text-primary" : "text-muted-foreground"
                            )}
                          >
                            {count}
                          </span>
                        )}
                      </button>
                    );
                  })}
                  {(!reactionStats?.reactions || Object.keys(reactionStats.reactions).length === 0) && (
                    <p className="text-sm text-muted-foreground">Nog geen reacties. Voeg de eerste toe!</p>
                  )}
                </div>
              </div>
            )}

            {/* Event URL link */}
            {event.url && (
              <div className="pt-4 border-t">
                <Button
                  asChild
                  size="sm"
                  variant="default"
                  className="w-full"
                >
                  <a href={event.url} target="_blank" rel="noopener noreferrer">
                    Open eventpagina
                  </a>
                </Button>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

export default EventDetailOverlay;

// Frontend/src/components/polls/PollCard.tsx
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import type { Poll, PollStats } from "@/lib/api";
import stemmenBg from "@/assets/stemmen.png";

export interface PollCardProps {
  poll: Poll;
  stats?: PollStats | null;
  selectedOption?: number;
  isSubmitting?: boolean;
  hasResponded?: boolean;
  onOptionSelect?: (pollId: number, optionId: number) => void;
  onSubmitVote?: (pollId: number) => void;
  className?: string;
}

export function PollCard({
  poll,
  stats,
  selectedOption,
  isSubmitting = false,
  hasResponded,
  onOptionSelect,
  onSubmitVote,
  className,
}: PollCardProps) {
  const hasResults = hasResponded ?? poll.user_has_responded;

  return (
    <Card className={cn("relative p-4 overflow-hidden", className)}>
      {/* Background Image Overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: `url(${stemmenBg})`,
          backgroundSize: "contain",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          opacity: 0.05,
        }}
      />

      {/* Content Layer - positioned above background */}
      <div className="relative z-10 space-y-3">
        <div>
          <h3 className="font-gilroy font-semibold text-lg text-foreground">{poll.title}</h3>
          <p className="text-sm text-muted-foreground mt-1">{poll.question}</p>
        </div>

        {hasResults ? (
          <div className="space-y-2 pt-2">
            <p className="text-sm font-gilroy font-medium text-foreground">Resultaten:</p>
            {poll.options.map((option) => {
              const count = stats?.option_counts[option.id] || 0;
              const totalResponses = stats?.total_responses || 0;
              const percentage = totalResponses > 0
                ? Math.round((count / totalResponses) * 100)
                : 0;
              const isSelected = selectedOption === option.id;
              return (
                <div key={option.id} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className={cn(
                      "text-foreground",
                      isSelected && "font-medium"
                    )}>
                      {option.option_text}
                      {isSelected && " ✓"}
                    </span>
                    <span className="text-muted-foreground font-medium">
                      {stats ? `${percentage}%` : "Laden..."}
                    </span>
                  </div>
                  {stats && (
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
            {stats && (
              <p className="text-xs text-muted-foreground pt-1">
                {stats.total_responses} {stats.total_responses === 1 ? "stem" : "stemmen"}
              </p>
            )}
            {!stats && (
              <p className="text-xs text-muted-foreground pt-1">
                Resultaten worden geladen...
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2 pt-2">
            {poll.options.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => onOptionSelect?.(poll.id, option.id)}
                disabled={hasResponded || isSubmitting}
                className={cn(
                  "w-full text-left p-3 rounded-lg border transition-colors",
                  "hover:border-primary hover:bg-primary/5",
                  "focus:outline-none focus:ring-2 focus:ring-primary/30",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  selectedOption === option.id
                    ? "border-primary bg-primary/10"
                    : "border-border"
                )}
              >
                {option.option_text}
              </button>
            ))}
            <Button
              onClick={() => onSubmitVote?.(poll.id)}
              disabled={!selectedOption || hasResponded || isSubmitting}
              className="w-full"
            >
              {isSubmitting ? "Stemmen..." : "Stem"}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

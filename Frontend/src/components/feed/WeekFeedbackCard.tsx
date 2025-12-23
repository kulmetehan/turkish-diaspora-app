// Frontend/src/components/feed/WeekFeedbackCard.tsx
import { cn } from "@/lib/ui/cn";

interface WeekFeedbackCardProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export function WeekFeedbackCard({ message, onDismiss, className }: WeekFeedbackCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-card overflow-hidden",
        "border border-border/50 shadow-soft",
        "p-4",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <p className="text-sm font-gilroy font-normal text-foreground">{message}</p>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 rounded"
            aria-label="Dismiss"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}



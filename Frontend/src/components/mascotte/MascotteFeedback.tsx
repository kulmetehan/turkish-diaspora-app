// Frontend/src/components/mascotte/MascotteFeedback.tsx
import { MascotteAvatar } from "@/components/onboarding/MascotteAvatar";
import { cn } from "@/lib/ui/cn";

export interface MascotteFeedbackProps {
  message: string;
  className?: string;
}

/**
 * Mascotte feedback component for displaying contextual messages.
 * Designed to be used with sonner toast.custom() for custom rendering.
 */
export function MascotteFeedback({ message, className }: MascotteFeedbackProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3",
        "rounded-xl bg-card border border-border/50 shadow-soft",
        "p-4",
        "min-w-[280px] max-w-[400px]",
        className
      )}
    >
      <div className="flex-shrink-0">
        <MascotteAvatar size="sm" />
      </div>
      <div className="flex-1">
        <p className="text-sm font-gilroy font-normal text-foreground leading-relaxed">
          {message}
        </p>
      </div>
    </div>
  );
}



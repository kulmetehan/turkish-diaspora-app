// Progress indicator component for onboarding carousel
import { cn } from "@/lib/ui/cn";

export interface OnboardingProgressProps {
  current: number;
  total: number;
  className?: string;
}

export function OnboardingProgress({ current, total, className }: OnboardingProgressProps) {
  return (
    <div className={cn("flex items-center justify-center gap-2", className)}>
      {Array.from({ length: total }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "h-2 w-2 rounded-full transition-all duration-300",
            index === current
              ? "bg-primary scale-125"
              : "bg-muted-foreground/30"
          )}
          aria-label={`Step ${index + 1} of ${total}`}
        />
      ))}
    </div>
  );
}


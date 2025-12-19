// Frontend/src/components/feed/EventBadge.tsx
import { cn } from "@/lib/ui/cn";

export interface EventBadgeProps {
  label?: string;
  className?: string;
}

export function EventBadge({ label = "Event", className }: EventBadgeProps) {
  return (
    <span
      className={cn(
        "absolute top-2 left-2 z-10",
        "inline-flex items-center rounded-full",
        "bg-brand-red px-2.5 py-0.5 text-xs font-gilroy font-semibold text-brand-white",
        "shadow-card",
        className
      )}
    >
      {label}
    </span>
  );
}






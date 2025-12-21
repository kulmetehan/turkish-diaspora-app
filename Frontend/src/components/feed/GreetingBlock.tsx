// Frontend/src/components/feed/GreetingBlock.tsx
import { cn } from "@/lib/ui/cn";

export interface GreetingBlockProps {
  userName?: string | null;
  className?: string;
}

function getTimeBasedGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) {
    return "Goedemorgen";
  } else if (hour < 18) {
    return "Goedemiddag";
  } else {
    return "Goedenavond";
  }
}

export function GreetingBlock({ userName, className }: GreetingBlockProps) {
  const greeting = getTimeBasedGreeting();
  const displayName = userName?.trim() || null;

  return (
    <div className={cn("px-4 py-1.5", className)}>
      <h2 className="text-2xl font-gilroy font-black text-foreground">
        {greeting}
        {displayName ? (
          <>
            {" "}
            <span className="text-primary">{displayName}</span>
          </>
        ) : null}
      </h2>
      <p className="mt-1 text-sm font-gilroy font-normal text-black">
        Wat er gebeurt in je omgeving...
      </p>
    </div>
  );
}









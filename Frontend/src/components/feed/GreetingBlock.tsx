// Frontend/src/components/feed/GreetingBlock.tsx
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export interface GreetingBlockProps {
  userName?: string | null;
  className?: string;
}

function getTimeBasedGreeting(t: (key: string) => string): string {
  const hour = new Date().getHours();
  if (hour < 12) {
    return t("feed.greeting.morning");
  } else if (hour < 18) {
    return t("feed.greeting.afternoon");
  } else {
    return t("feed.greeting.evening");
  }
}

export function GreetingBlock({ userName, className }: GreetingBlockProps) {
  const { t } = useTranslation();
  const greeting = getTimeBasedGreeting(t);
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
        {t("feed.greeting.subtitle")}
      </p>
    </div>
  );
}











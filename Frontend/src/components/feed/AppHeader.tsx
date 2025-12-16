// Frontend/src/components/feed/AppHeader.tsx
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";

export interface AppHeaderProps {
  onNotificationClick?: () => void;
  className?: string;
}

export function AppHeader({ onNotificationClick, className }: AppHeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center justify-between px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-3",
        className
      )}
    >
      {/* Logo/Wordmark */}
      <div className="flex items-center">
        <h1 className="text-4xl font-gilroy font-black text-foreground tracking-tight">
          Kom<span className="text-[hsl(var(--brand-red-strong))]">ş</span>u
        </h1>
      </div>

      {/* Notification Bell */}
      <button
        type="button"
        onClick={onNotificationClick}
        className={cn(
          "flex h-11 w-11 items-center justify-center rounded-full",
          "text-muted-foreground transition-colors",
          "hover:bg-muted hover:text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
        )}
        aria-label="Notifications"
      >
        <Icon name="Bell" sizeRem={1.25} decorative={false} title="Notifications" />
      </button>
    </header>
  );
}



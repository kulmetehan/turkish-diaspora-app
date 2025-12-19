// Frontend/src/components/feed/AppHeader.tsx
import TurkSpotBot from "@/assets/turkspotbot.png";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";

export interface AppHeaderProps {
  onNotificationClick?: () => void;
  showSearch?: boolean;
  onSearchToggle?: () => void;
  className?: string;
}

export function AppHeader({
  onNotificationClick,
  showSearch = false,
  onSearchToggle,
  className
}: AppHeaderProps) {
  const navigate = useNavigate();

  const handleLogoClick = () => {
    navigate("/feed");
  };

  return (
    <header
      className={cn(
        "flex items-center justify-between px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-3",
        className
      )}
    >
      {/* Logo/Wordmark with mascot */}
      <button
        type="button"
        onClick={handleLogoClick}
        className="flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 rounded-sm"
        aria-label="Go to home"
      >
        <h1 className="text-4xl font-gilroy font-black text-foreground tracking-tight">
          <span className="text-[hsl(var(--brand-red-strong))]">T</span>urk
          <span className="text-[hsl(var(--brand-red-strong))]">S</span>pot
          <span className="text-[hsl(var(--brand-red-strong))] text-2xl font-mono align-top">AI</span>
        </h1>
        <img
          src={TurkSpotBot}
          alt="TurkSpot Bot mascot"
          className="h-12 w-auto object-contain"
        />
      </button>

      {/* Right side: Search toggle (replaces bell for news page) or Notification Bell */}
      {onSearchToggle ? (
        <button
          type="button"
          onClick={onSearchToggle}
          className={cn(
            "flex h-11 w-11 items-center justify-center rounded-full",
            "text-muted-foreground transition-colors",
            "hover:bg-muted hover:text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
          )}
          aria-label="Search"
        >
          <Icon name="Search" sizeRem={1.25} decorative={false} title="Search" />
        </button>
      ) : (
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
      )}
    </header>
  );
}






// Frontend/src/components/feed/AppHeader.tsx
import { useEffect, useState } from "react";
import TurkSpotBot from "@/assets/turkspotbot.png";
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";
import { useUserAuth } from "@/hooks/useUserAuth";
import { getCurrentUser } from "@/lib/api";
import { AccountOverlay } from "@/components/account/AccountOverlay";
import { LoginModal } from "@/components/auth/LoginModal";
import { User } from "lucide-react";

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
  const { isAuthenticated, isLoading } = useUserAuth();
  const [profile, setProfile] = useState<{ name: string | null; avatar_url: string | null } | null>(null);
  const [accountOverlayOpen, setAccountOverlayOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      getCurrentUser()
        .then((user) => {
          setProfile(user);
        })
        .catch((error) => {
          console.error("Failed to load profile:", error);
        });
    } else {
      setProfile(null);
    }
  }, [isAuthenticated, isLoading]);

  const handleLogoClick = () => {
    navigate("/feed");
  };

  function getInitials(name: string | null | undefined): string {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  return (
    <>
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

        {/* Right side: Search toggle, Account button, or Login button */}
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
        ) : isAuthenticated ? (
          <button
            type="button"
            onClick={() => setAccountOverlayOpen(true)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-full",
              "text-muted-foreground transition-colors",
              "hover:bg-muted hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
            )}
            aria-label="Account"
          >
            {profile?.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.name || "Avatar"}
                className="h-8 w-8 rounded-full object-cover border-2 border-primary/20"
              />
            ) : (
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-xs border-2 border-primary/20">
                {getInitials(profile?.name)}
              </div>
            )}
            <span className="hidden sm:inline text-sm font-medium">
              {profile?.name || "Account"}
            </span>
          </button>
        ) : (
          <Button
            type="button"
            onClick={() => setLoginModalOpen(true)}
            variant="default"
            size="md"
            className="gap-2"
            aria-label="Inloggen / Registreren"
          >
            <Icon name="LogIn" sizeRem={1.1} decorative={false} title="Inloggen" />
            <span className="text-sm font-medium">Inloggen</span>
          </Button>
        )}
      </header>

      {/* Account Overlay */}
      <AccountOverlay open={accountOverlayOpen} onOpenChange={setAccountOverlayOpen} />

      {/* Login Modal */}
      <LoginModal open={loginModalOpen} onOpenChange={setLoginModalOpen} />
    </>
  );
}












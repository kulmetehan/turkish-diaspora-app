// Frontend/src/components/account/AccountLoginSection.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCurrentUser } from "@/lib/api";
import { User } from "lucide-react";

interface AccountLoginSectionProps {
  isAuthenticated: boolean;
  email: string | null;
  userId: string | null;
  onLogout: () => void;
  className?: string;
}

export function AccountLoginSection({
  isAuthenticated,
  email,
  userId,
  onLogout,
  className,
}: AccountLoginSectionProps) {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<{ name: string | null; avatar_url: string | null } | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AccountLoginSection.tsx:28',message:'AccountLoginSection loadProfile START',data:{isAuthenticated,userId},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      getCurrentUser()
        .then((user) => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/37069a88-cc21-4ee6-bcd0-7b771fa9b5c4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AccountLoginSection.tsx:31',message:'AccountLoginSection getCurrentUser returned',data:{name:user?.name,avatar_url:user?.avatar_url,avatar_url_length:user?.avatar_url?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
          // #endregion
          setProfile(user);
        })
        .catch((error) => {
          console.error("Failed to load profile:", error);
        });
    }
  }, [isAuthenticated]);

  function getInitials(name: string | null | undefined): string {
    if (!name) return "?";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  if (!isAuthenticated) {
    return (
      <div className={cn("rounded-xl bg-surface-muted/50 p-4", className)}>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h2 className="text-lg font-gilroy font-medium text-foreground">Niet ingelogd</h2>
            <p className="text-sm text-muted-foreground">
              Log in of maak een account aan om je activiteit bij te houden
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            onClick={() => navigate("/auth")}
            className="inline-flex items-center gap-2"
          >
            <Icon name="LogIn" className="h-4 w-4" aria-hidden />
            <span>Inloggen / Registreren</span>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-xl bg-surface-muted/50 p-4", className)}>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile.name || "Avatar"}
              className="w-10 h-10 rounded-full object-cover border-2 border-primary/20"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-gilroy font-semibold text-sm border-2 border-primary/20">
              {getInitials(profile?.name)}
            </div>
          )}
          <div className="space-y-1">
            <h2 className="text-lg font-gilroy font-medium text-foreground">
              {profile?.name || email || "Account"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {email || "Gebruiker"}
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onLogout}
          className="inline-flex items-center gap-2"
        >
          <Icon name="LogOut" className="h-4 w-4" aria-hidden />
          <span>Uitloggen</span>
        </Button>
      </div>
    </div>
  );
}




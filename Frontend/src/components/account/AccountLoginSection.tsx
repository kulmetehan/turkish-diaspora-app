// Frontend/src/components/account/AccountLoginSection.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";

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
        <div className="space-y-1">
          <h2 className="text-lg font-gilroy font-medium text-foreground">Account</h2>
          <p className="text-sm text-muted-foreground">
            {email || "Gebruiker"} {userId ? `(${userId.slice(0, 8)}...)` : ""}
          </p>
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

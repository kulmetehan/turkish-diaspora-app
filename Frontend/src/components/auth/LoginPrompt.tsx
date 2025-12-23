// Frontend/src/components/auth/LoginPrompt.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";

interface LoginPromptProps {
  message?: string;
  className?: string;
  onLoginClick?: () => void;
}

export function LoginPrompt({ message, className, onLoginClick }: LoginPromptProps) {
  const navigate = useNavigate();

  const handleLoginClick = () => {
    if (onLoginClick) {
      onLoginClick();
    } else {
      navigate("/auth");
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl bg-surface-muted/50 p-4 text-center",
        "border-0",
        className
      )}
    >
      <div className="flex flex-col items-center gap-3">
        <Icon name="LogIn" className="h-5 w-5 text-muted-foreground" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">
            {message || "Log in om deze actie uit te voeren"}
          </p>
          <p className="text-xs text-muted-foreground">
            Maak een account aan of log in om verder te gaan
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={handleLoginClick}
          className="mt-1"
        >
          <Icon name="LogIn" className="mr-2 h-4 w-4" />
          Inloggen / Registreren
        </Button>
      </div>
    </div>
  );
}



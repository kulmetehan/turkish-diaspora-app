// Frontend/src/components/auth/LoginPrompt.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import { useNavigate } from "react-router-dom";
import { GoogleLoginButton } from "@/components/auth/GoogleLoginButton";
import { useTranslation } from "@/hooks/useTranslation";

interface LoginPromptProps {
  message?: string;
  className?: string;
  onLoginClick?: () => void;
}

export function LoginPrompt({ message, className, onLoginClick }: LoginPromptProps) {
  const { t } = useTranslation();
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
            {message || t("auth.loginPrompt.title")}
          </p>
          <p className="text-xs text-muted-foreground">
            {t("auth.loginPrompt.subtitle")}
          </p>
        </div>
        <div className="flex flex-col gap-2 w-full">
          <GoogleLoginButton
            size="sm"
            fullWidth
            onSuccess={() => {
              // Success is handled by useUserAuth hook
            }}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleLoginClick}
            className="mt-1"
          >
            <Icon name="LogIn" className="mr-2 h-4 w-4" />
            {t("auth.loginPrompt.emailPassword")}
          </Button>
        </div>
      </div>
    </div>
  );
}



// Frontend/src/components/share/ShareButton.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";
import { toast } from "sonner";
import { share, shareLocation, sharePoll, type ShareData } from "@/lib/share";

interface ShareButtonProps {
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
  className?: string;
  location?: {
    id: number | string;
    name: string;
    category?: string | null;
  };
  poll?: {
    id: number | string;
    title: string;
    question?: string;
  };
  customData?: ShareData;
}

export function ShareButton({
  variant = "outline",
  size = "default",
  className,
  location,
  poll,
  customData,
}: ShareButtonProps) {
  const [isSharing, setIsSharing] = useState(false);

  const handleShare = async () => {
    setIsSharing(true);
    try {
      let success = false;

      if (location) {
        success = await shareLocation(location);
      } else if (poll) {
        success = await sharePoll(poll);
      } else if (customData) {
        success = await share(customData);
      }

      if (success) {
        // Check if it was copied to clipboard (no native share dialog)
        if (typeof navigator !== "undefined" && !("share" in navigator)) {
          toast.success("Link gekopieerd naar klembord");
        }
      }
    } catch (error) {
      console.error("Share failed:", error);
      toast.error("Delen mislukt", {
        description: "Probeer het opnieuw of kopieer de link handmatig.",
      });
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleShare}
      disabled={isSharing}
      className={className}
      aria-label="Deel"
    >
      <Icon name={isSharing ? "Loader2" : "Share2"} className="h-4 w-4" />
      {size !== "icon" && <span className="ml-2">{isSharing ? "Delen..." : "Deel"}</span>}
    </Button>
  );
}


// Frontend/src/components/share/ShareButton.tsx
import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { share, shareEvent, shareLocation, sharePoll, type ShareData } from "@/lib/share";
import { useState } from "react";
import { toast } from "sonner";

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
  event?: {
    id: number | string;
    title: string;
  };
  customData?: ShareData;
}

export function ShareButton({
  variant = "outline",
  size = "default",
  className,
  location,
  poll,
  event,
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
      } else if (event) {
        success = await shareEvent(event);
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
      {size !== "icon" && !isSharing && <span className="ml-2">Deel</span>}
    </Button>
  );
}


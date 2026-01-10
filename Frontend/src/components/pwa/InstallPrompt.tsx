// Frontend/src/components/pwa/InstallPrompt.tsx
// Install prompt component for PWA installation

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import {
  getDeferredPrompt,
  setDeferredPrompt,
  showInstallPrompt,
  isInstallPromptAvailable,
  isAppInstalled,
  getPlatform,
  type BeforeInstallPromptEvent,
} from "@/lib/pwa";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

export function InstallPrompt() {
  const [showPrompt, setShowPrompt] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    // Don't show if already installed
    if (isAppInstalled()) {
      return;
    }

    // Don't show if browser doesn't support install prompt
    if (!isInstallPromptAvailable()) {
      return;
    }

    // Check if user has dismissed the prompt before (stored in localStorage)
    const dismissed = localStorage.getItem("pwa-install-dismissed");
    if (dismissed) {
      const dismissedTime = parseInt(dismissed, 10);
      const now = Date.now();
      // Show again after 7 days
      if (now - dismissedTime < 7 * 24 * 60 * 60 * 1000) {
        return;
      }
    }

    // Listen for beforeinstallprompt event
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setShowPrompt(true);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstall = async () => {
    setIsInstalling(true);
    try {
      const accepted = await showInstallPrompt();
      if (accepted) {
        setShowPrompt(false);
        // Track install event (if analytics is available)
        if (typeof window !== "undefined" && (window as any).posthog) {
          (window as any).posthog.capture("pwa_installed");
        }
      }
    } catch (error) {
      console.error("Error showing install prompt:", error);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    setIsDismissed(true);
    // Store dismissal in localStorage
    localStorage.setItem("pwa-install-dismissed", Date.now().toString());
  };

  // Don't render if prompt shouldn't be shown
  if (!showPrompt || isDismissed || isAppInstalled()) {
    return null;
  }

  const platform = getPlatform();
  const isIOS = platform === "ios";

  return (
    <div
      className={cn(
        "fixed bottom-20 left-0 right-0 z-50 mx-auto max-w-md px-4",
        "animate-in slide-in-from-bottom-4 duration-300"
      )}
    >
      <div className="rounded-lg bg-background border border-border shadow-lg p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1">Installeer Turkspot</h3>
            <p className="text-xs text-muted-foreground mb-3">
              {isIOS
                ? "Voeg Turkspot toe aan je startscherm voor een betere ervaring."
                : "Installeer de app voor snellere toegang en offline gebruik."}
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleInstall}
                disabled={isInstalling}
                className="flex-1"
              >
                {isInstalling ? "Installeren..." : "Installeer"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDismiss}
                className="px-2"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            {isIOS && (
              <p className="text-xs text-muted-foreground mt-2">
                Tik op het menu en selecteer "Voeg toe aan startscherm"
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}



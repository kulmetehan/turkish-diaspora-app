// Frontend/src/lib/pwa.ts
// PWA utilities for service worker registration and install prompt handling

/**
 * Register service worker for PWA functionality.
 * This is separate from push notification registration and runs automatically on app start.
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) {
    console.warn("Service workers not supported");
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });

    console.log("Service worker registered:", registration.scope);

    // Check for updates periodically
    let updatePromptShown = false;
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing;
      if (newWorker) {
        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "installed" && navigator.serviceWorker.controller && !updatePromptShown) {
            // New service worker available, prompt user to refresh
            console.log("New service worker available. Refresh to update.");
            updatePromptShown = true; // Prevent multiple prompts
            // Optionally show a notification to the user
            if (window.confirm("Nieuwe versie beschikbaar! Wil je de app bijwerken?")) {
              window.location.reload();
            }
          }
        });
      }
    });

    return registration;
  } catch (error) {
    console.error("Service worker registration failed:", error);
    return null;
  }
}

/**
 * Check if app is installed (running in standalone mode).
 */
export function isAppInstalled(): boolean {
  // Check for standalone mode (iOS Safari, Android Chrome)
  if (window.matchMedia("(display-mode: standalone)").matches) {
    return true;
  }

  // Check for iOS standalone mode
  if ((window.navigator as any).standalone === true) {
    return true;
  }

  return false;
}

/**
 * Detect platform for install prompt handling.
 */
export function getPlatform(): "ios" | "android" | "desktop" | "unknown" {
  const userAgent = navigator.userAgent.toLowerCase();

  if (/iphone|ipad|ipod/.test(userAgent)) {
    return "ios";
  }

  if (/android/.test(userAgent)) {
    return "android";
  }

  if (/windows|mac|linux/.test(userAgent) && !/mobile/.test(userAgent)) {
    return "desktop";
  }

  return "unknown";
}

/**
 * Store install prompt event for later use.
 */
let deferredPrompt: BeforeInstallPromptEvent | null = null;

export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/**
 * Get stored install prompt event.
 */
export function getDeferredPrompt(): BeforeInstallPromptEvent | null {
  return deferredPrompt;
}

/**
 * Set install prompt event (called from InstallPrompt component).
 */
export function setDeferredPrompt(event: BeforeInstallPromptEvent | null): void {
  deferredPrompt = event;
}

/**
 * Show install prompt (call this when user clicks install button).
 */
export async function showInstallPrompt(): Promise<boolean> {
  if (!deferredPrompt) {
    return false;
  }

  try {
    // Show the install prompt
    await deferredPrompt.prompt();

    // Wait for user response
    const { outcome } = await deferredPrompt.userChoice;

    // Clear the deferred prompt
    deferredPrompt = null;

    return outcome === "accepted";
  } catch (error) {
    console.error("Error showing install prompt:", error);
    deferredPrompt = null;
    return false;
  }
}

/**
 * Check if install prompt is available (browser supports it and app is not installed).
 */
export function isInstallPromptAvailable(): boolean {
  // Don't show if already installed
  if (isAppInstalled()) {
    return false;
  }

  // Check if browser supports beforeinstallprompt
  return "onbeforeinstallprompt" in window;
}


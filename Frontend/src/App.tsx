// src/App.tsx
// Unified HomePage container that mounts all four main tabs (Map, News, Events, Feed)
// as persistent layers with visibility toggling based on activeTab from navigation store.
// The URL is the source of truth; activeTab reflects the current pathname.

import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import MapTab from "@/components/MapTab";
import { cn } from "@/lib/ui/cn";
import EventsPage from "@/pages/EventsPage";
import FeedPage from "@/pages/FeedPage";
import NewsPage from "@/pages/NewsPage";
import { navigationActions, useActiveTab, type TabId } from "@/state/navigation";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { getOnboardingStatus, type OnboardingStatus } from "@/lib/api";

interface HomePageProps {
  initialTab?: TabId;
}

function HomePage({ initialTab }: HomePageProps) {
  const location = useLocation();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);

  // Derive activeTab from URL pathname (URL is source of truth)
  const tabFromPath: TabId =
    location.pathname.startsWith("/news") ? "news" :
      location.pathname.startsWith("/events") ? "events" :
        location.pathname.startsWith("/map") ? "map" :
          "feed";

  // Sync URL to navigation store on mount and route changes
  // URL is source of truth; initialTab is only a fallback if pathname doesn't match expected routes
  useEffect(() => {
    // Always use tabFromPath (derived from URL) as source of truth
    // initialTab is only used as fallback if somehow pathname doesn't match (shouldn't happen in normal flow)
    const tabToSet = tabFromPath;
    navigationActions.setActiveTab(tabToSet);
  }, [location.pathname, tabFromPath]);

  // Check onboarding status on mount (applies to all tabs)
  useEffect(() => {
    try {
      const status = getOnboardingStatus();
      console.log("[HomePage] Onboarding status:", status);
      setOnboardingStatus(status);
      if (status.first_run) {
        console.log("[HomePage] Showing onboarding (first_run=true)");
        setShowOnboarding(true);
      } else {
        console.log("[HomePage] Not showing onboarding (first_run=false)");
        setShowOnboarding(false);
      }
    } catch (error) {
      console.error("Failed to load onboarding status:", error);
      // Default to showing onboarding if we can't determine status
      setShowOnboarding(true);
    }
  }, []);

  // Read activeTab from store for visibility toggling
  const activeTab = useActiveTab();

  // Render all tabs (they'll be behind the onboarding overlay if onboarding is active)
  const tabsContent = (
    <>
      {/* Map layer */}
      <div
        className={cn(
          "absolute inset-0",
          activeTab === "map" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        <MapTab />
      </div>

      {/* News layer */}
      <div
        className={cn(
          "absolute inset-0 overflow-auto",
          activeTab === "news" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        <NewsPage />
      </div>

      {/* Events layer */}
      <div
        className={cn(
          "absolute inset-0 overflow-auto",
          activeTab === "events" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        <EventsPage />
      </div>

      {/* Feed layer */}
      <div
        className={cn(
          "absolute inset-0 overflow-auto",
          activeTab === "feed" ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      >
        <FeedPage />
      </div>
    </>
  );

  // Show onboarding overlay if first_run is true (applies to all tabs)
  if (showOnboarding && onboardingStatus?.first_run) {
    return (
      <div className="relative h-[calc(100svh-var(--footer-height))] w-full overflow-hidden">
        {tabsContent}
        {/* Onboarding overlay on top of everything */}
        <OnboardingFlow
          onComplete={() => {
            setShowOnboarding(false);
            // Reload page to ensure all components refresh with new onboarding status
            window.location.reload();
          }}
        />
      </div>
    );
  }

  return (
    <div className="relative h-[calc(100svh-var(--footer-height))] w-full overflow-hidden">
      {tabsContent}
    </div>
  );
}

export default HomePage;

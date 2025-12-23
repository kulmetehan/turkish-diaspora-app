// src/App.tsx
// Unified HomePage container that mounts all four main tabs (Map, News, Events, Feed)
// as persistent layers with visibility toggling based on activeTab from navigation store.
// The URL is the source of truth; activeTab reflects the current pathname.

import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import MapTab from "@/components/MapTab";
import { cn } from "@/lib/ui/cn";
import EventsPage from "@/pages/EventsPage";
import FeedPage from "@/pages/FeedPage";
import NewsPage from "@/pages/NewsPage";
import { navigationActions, useActiveTab, type TabId } from "@/state/navigation";

interface HomePageProps {
  initialTab?: TabId;
}

function HomePage({ initialTab }: HomePageProps) {
  const location = useLocation();

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

  // Read activeTab from store for visibility toggling
  const activeTab = useActiveTab();

  return (
    <div className="relative h-[calc(100svh-var(--footer-height))] w-full overflow-hidden">
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
    </div>
  );
}

export default HomePage;

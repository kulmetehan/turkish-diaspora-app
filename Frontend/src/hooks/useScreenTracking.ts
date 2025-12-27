// Frontend/src/hooks/useScreenTracking.ts
// Automatic screen tracking hook for React Router routes

import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { trackScreenView, getSourceFromLocation } from "@/lib/analytics";

/**
 * Map pathname to screen name
 */
function getScreenNameFromPath(pathname: string): string {
  // Remove leading slash and hash (for HashRouter)
  const cleanPath = pathname.replace(/^\/+/, "").replace(/^#\/+/, "");

  if (cleanPath === "" || cleanPath === "feed") return "feed";
  if (cleanPath.startsWith("map")) return "map";
  if (cleanPath.startsWith("news")) return "news";
  if (cleanPath.startsWith("events")) return "events";
  if (cleanPath.startsWith("locations/")) {
    // Extract location ID from path
    const match = cleanPath.match(/locations\/(\d+)/);
    if (match) {
      return "location_detail";
    }
    return "location_detail";
  }
  if (cleanPath.startsWith("claim/")) {
    return "claim_page";
  }
  if (cleanPath === "account") return "account";
  if (cleanPath === "privacy") return "privacy";
  if (cleanPath === "terms") return "terms";
  if (cleanPath === "guidelines") return "guidelines";
  if (cleanPath === "pulse") return "diaspora_pulse";
  if (cleanPath.startsWith("polls/")) {
    return "poll_detail";
  }
  if (cleanPath.startsWith("admin")) return "admin";

  return "unknown";
}

/**
 * Extract metadata from pathname and search
 */
function getMetadataFromLocation(pathname: string, search: string): Record<string, any> {
  const metadata: Record<string, any> = {};

  // Extract location_id from /locations/:id
  const locationMatch = pathname.match(/locations\/(\d+)/);
  if (locationMatch) {
    metadata.location_id = parseInt(locationMatch[1], 10);
  }

  // Extract claim_token from /claim/:token
  const claimMatch = pathname.match(/claim\/([^/?]+)/);
  if (claimMatch) {
    metadata.claim_token = claimMatch[1];
  }

  // Extract poll_id from /polls/:id
  const pollMatch = pathname.match(/polls\/(\d+)/);
  if (pollMatch) {
    metadata.poll_id = parseInt(pollMatch[1], 10);
  }

  // Include search params if present
  if (search) {
    metadata.search = search;
  }

  return metadata;
}

/**
 * Hook to automatically track screen views on route changes
 * Should be used in AppLayout or root component
 */
export function useScreenTracking(): void {
  const location = useLocation();

  useEffect(() => {
    // Get screen name from pathname
    const screenName = getScreenNameFromPath(location.pathname);

    // Get source from location (URL params, referrer, etc.)
    const source = getSourceFromLocation(location);

    // Get additional metadata
    const metadata = getMetadataFromLocation(location.pathname, location.search);

    // Track screen view
    trackScreenView(screenName, source, {
      pathname: location.pathname,
      ...metadata,
    });
  }, [location]);
}


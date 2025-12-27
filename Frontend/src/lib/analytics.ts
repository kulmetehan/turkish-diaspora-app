// Frontend/src/lib/analytics.ts
// PostHog Analytics Service
// Provides centralized analytics tracking for the Turkish Diaspora App

import { getOrCreateClientId } from "./api";
import type { Location } from "react-router-dom";
import posthog from "posthog-js";

// PostHog instance - will be initialized on app start
let posthogInitialized = false;


/**
 * Initialize PostHog analytics
 * Should be called once on app startup
 */
export function initAnalytics(): void {
  // Only initialize if PostHog key is provided
  const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
  if (!posthogKey) {
    if (import.meta.env.DEV) {
      console.debug("[Analytics] PostHog key not found, analytics disabled");
    }
    return;
  }

  try {
    const posthogHost = import.meta.env.VITE_POSTHOG_HOST || "https://app.posthog.com";

    posthog.init(posthogKey, {
      api_host: posthogHost,
      loaded: (phInstance: any) => {
        // Sync client_id with PostHog
        const clientId = getOrCreateClientId();
        phInstance.identify(clientId);
        posthogInitialized = true;

        if (import.meta.env.DEV) {
          console.debug("[Analytics] PostHog initialized with client_id:", clientId);
        }
      },
      // Disable autocapture in development to reduce noise
      autocapture: !import.meta.env.DEV,
      // Capture pageviews manually via screen_viewed events
      capture_pageview: false,
      // Respect user privacy
      respect_dnt: true,
    });
  } catch (error) {
    // Analytics failures should not break the app
    console.error("[Analytics] Failed to initialize PostHog:", error);
  }
}

/**
 * Identify user with PostHog
 * Call this when user logs in
 */
export function identifyUser(userId: string, email?: string | null): void {
  if (!posthogInitialized) return;

  try {
    posthog.identify(userId, {
      email: email || undefined,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] User identified:", userId);
    }
  } catch (error) {
    console.error("[Analytics] Failed to identify user:", error);
  }
}

/**
 * Reset user identity
 * Call this when user logs out
 */
export function resetUser(): void {
  if (!posthogInitialized) return;

  try {
    posthog.reset();
    // Re-identify with client_id after reset
    const clientId = getOrCreateClientId();
    posthog.identify(clientId);

    if (import.meta.env.DEV) {
      console.debug("[Analytics] User reset, re-identified with client_id:", clientId);
    }
  } catch (error) {
    console.error("[Analytics] Failed to reset user:", error);
  }
}

/**
 * Get source from location (URL parameters, referrer, etc.)
 */
export function getSourceFromLocation(location: Location): string {
  // Check URL parameters first
  const searchParams = new URLSearchParams(location.search);
  const sourceParam = searchParams.get("source");
  if (sourceParam) {
    return sourceParam;
  }

  // Check hash parameters (for HashRouter)
  const hash = window.location.hash;
  if (hash.includes("?")) {
    const hashParams = new URLSearchParams(hash.split("?")[1]);
    const hashSource = hashParams.get("source");
    if (hashSource) {
      return hashSource;
    }
  }

  // Check referrer
  const referrer = document.referrer;
  if (referrer) {
    try {
      const referrerUrl = new URL(referrer);
      // If referrer is from same origin, check if it's a specific route
      if (referrerUrl.origin === window.location.origin) {
        const referrerPath = referrerUrl.pathname + referrerUrl.hash;
        if (referrerPath.includes("/map")) return "map";
        if (referrerPath.includes("/feed")) return "feed";
        if (referrerPath.includes("/news")) return "news";
        if (referrerPath.includes("/events")) return "events";
      }
    } catch {
      // Invalid referrer URL, ignore
    }
  }

  // Default to navigation
  return "navigation";
}

/**
 * Track screen view
 */
export function trackScreenView(
  screenName: string,
  source?: string,
  metadata?: Record<string, any>
): void {
  if (!posthogInitialized) return;

  try {
    const eventProperties = {
      screen_name: screenName,
      source: source || "unknown",
      ...metadata,
    };
    
    posthog.capture("screen_viewed", eventProperties);

    if (import.meta.env.DEV) {
      console.debug("[Analytics] screen_viewed:", screenName, source, metadata);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track screen view:", error);
  }
}

/**
 * Track location view
 */
export function trackLocationView(locationId: number, source: string): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("location_viewed", {
      location_id: locationId,
      source,
      screen_name: "location_detail",
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] location_viewed:", locationId, source);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track location view:", error);
  }
}

/**
 * Track claim CTA click
 */
export function trackClaimCTAClick(
  locationId: number,
  source: string,
  claimStatus?: string
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("claim_cta_clicked", {
      location_id: locationId,
      source,
      claim_status: claimStatus || "unknown",
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] claim_cta_clicked:", locationId, source, claimStatus);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track claim CTA click:", error);
  }
}

/**
 * Track contact CTA click
 */
export function trackContactCTAClick(locationId: number, source: string): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("contact_cta_clicked", {
      location_id: locationId,
      source,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] contact_cta_clicked:", locationId, source);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track contact CTA click:", error);
  }
}

/**
 * Track claim flow started
 */
export function trackClaimFlowStarted(
  locationId: number,
  claimToken: string,
  source: "claim_page" | "claim_dialog"
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("claim_flow_started", {
      location_id: locationId,
      claim_token: claimToken,
      source,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] claim_flow_started:", locationId, claimToken, source);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track claim flow started:", error);
  }
}

/**
 * Track claim flow completed
 */
export function trackClaimFlowCompleted(
  locationId: number,
  claimToken: string,
  source: "claim_page" | "claim_dialog",
  hasDescription: boolean,
  flowDurationMs: number
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("claim_flow_completed", {
      location_id: locationId,
      claim_token: claimToken,
      source,
      has_description: hasDescription,
      flow_duration_ms: flowDurationMs,
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] claim_flow_completed:",
        locationId,
        claimToken,
        source,
        hasDescription,
        flowDurationMs
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track claim flow completed:", error);
  }
}

/**
 * Track claim flow abandoned
 */
export function trackClaimFlowAbandoned(
  locationId: number,
  claimToken: string,
  source: "claim_page" | "claim_dialog",
  reason?: "navigate_away" | "dialog_closed" | "page_close",
  flowDurationMs?: number
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("claim_flow_abandoned", {
      location_id: locationId,
      claim_token: claimToken,
      source,
      reason: reason || "unknown",
      flow_duration_ms: flowDurationMs || 0,
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] claim_flow_abandoned:",
        locationId,
        claimToken,
        source,
        reason,
        flowDurationMs
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track claim flow abandoned:", error);
  }
}

/**
 * Track help opened
 */
export function trackHelpOpened(source: string): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("help_opened", {
      source,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] help_opened:", source);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track help opened:", error);
  }
}

/**
 * Track FAQ opened
 */
export function trackFAQOpened(source: string): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("faq_opened", {
      source,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] faq_opened:", source);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track FAQ opened:", error);
  }
}

/**
 * Track info icon clicked
 */
export function trackInfoClicked(context: string): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("info_clicked", {
      context,
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] info_clicked:", context);
    }
  } catch (error) {
    console.error("[Analytics] Failed to track info clicked:", error);
  }
}

// ============================================================================
// Onboarding Tracking
// ============================================================================

/**
 * Track onboarding started
 */
export function trackOnboardingStarted(): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("onboarding_started", {
      timestamp: new Date().toISOString(),
    });

    if (import.meta.env.DEV) {
      console.debug("[Analytics] onboarding_started");
    }
  } catch (error) {
    console.error("[Analytics] Failed to track onboarding started:", error);
  }
}

/**
 * Track onboarding screen viewed
 */
export function trackOnboardingScreenViewed(
  screenNumber: number,
  screenName: string,
  timeOnPreviousScreenMs?: number
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("onboarding_screen_viewed", {
      screen_number: screenNumber,
      screen_name: screenName,
      time_on_previous_screen_ms: timeOnPreviousScreenMs,
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] onboarding_screen_viewed:",
        screenNumber,
        screenName,
        timeOnPreviousScreenMs
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track onboarding screen:", error);
  }
}

/**
 * Track onboarding data collected
 */
export function trackOnboardingDataCollected(
  screenNumber: number,
  screenName: string,
  dataType: "home_city" | "memleket" | "gender" | "username" | "avatar",
  value?: string | string[] | null
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("onboarding_data_collected", {
      screen_number: screenNumber,
      screen_name: screenName,
      data_type: dataType,
      value: value || null,
      has_value: value !== null && value !== undefined,
      // For memleket, also track count
      ...(dataType === "memleket" && Array.isArray(value)
        ? { memleket_count: value.length }
        : {}),
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] onboarding_data_collected:",
        screenNumber,
        screenName,
        dataType,
        value
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track onboarding data:", error);
  }
}

/**
 * Track onboarding completed
 */
export function trackOnboardingCompleted(
  data: {
    home_city?: string | null;
    home_city_key?: string | null;
    memleket?: string[] | null;
    gender?: string | null;
    has_username?: boolean;
    has_avatar?: boolean;
  },
  totalDurationMs: number,
  screensCompleted: number
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("onboarding_completed", {
      home_city: data.home_city || null,
      home_city_key: data.home_city_key || null,
      memleket_count: data.memleket?.length || 0,
      has_memleket: (data.memleket?.length || 0) > 0,
      gender: data.gender || null,
      has_username: data.has_username || false,
      has_avatar: data.has_avatar || false,
      total_duration_ms: totalDurationMs,
      screens_completed: screensCompleted,
      onboarding_version: "v1.0",
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] onboarding_completed:",
        data,
        totalDurationMs,
        screensCompleted
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track onboarding completed:", error);
  }
}

/**
 * Track onboarding abandoned
 */
export function trackOnboardingAbandoned(
  screenNumber: number,
  screenName: string,
  reason?: "navigate_away" | "close_app" | "timeout" | "user_action",
  durationMs?: number
): void {
  if (!posthogInitialized) return;

  try {
    posthog.capture("onboarding_abandoned", {
      screen_number: screenNumber,
      screen_name: screenName,
      reason: reason || "unknown",
      duration_ms: durationMs || 0,
    });

    if (import.meta.env.DEV) {
      console.debug(
        "[Analytics] onboarding_abandoned:",
        screenNumber,
        screenName,
        reason,
        durationMs
      );
    }
  } catch (error) {
    console.error("[Analytics] Failed to track onboarding abandoned:", error);
  }
}


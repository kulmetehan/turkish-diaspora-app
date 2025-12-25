// Frontend/src/lib/api.ts
import { supabase } from "@/lib/supabaseClient";
import { toast } from "sonner";
import type { LocationMarker } from "@/api/fetchLocations";

/**
 * Normalize API base URL: remove /api/v1 if present, we add it in paths.
 * This ensures consistent behavior whether VITE_API_BASE_URL includes /api/v1 or not.
 * 
 * @param raw - The raw API base URL from environment variable
 * @returns Normalized base URL (host only, no trailing slash, no /api/v1)
 */
export function normalizeApiBase(raw: string | undefined): string {
  if (!raw) return "";
  // Remove trailing slashes
  let base = raw.replace(/\/+$/, "");
  // Remove /api/v1 if it exists at the end
  if (base.endsWith("/api/v1")) {
    base = base.slice(0, -7); // Remove "/api/v1"
  }
  return base;
}

// API_BASE should be just the backend origin (no trailing slash, no /api/v1)
// In production builds, Vite replaces import.meta.env.VITE_API_BASE_URL at build time
// If not set, it will be undefined and normalizeApiBase returns empty string
export const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE_URL);

// Debug logging in development to help troubleshoot environment variable issues
if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.debug("[API_BASE] VITE_API_BASE_URL:", import.meta.env.VITE_API_BASE_URL);
  // eslint-disable-next-line no-console
  console.debug("[API_BASE] Normalized:", API_BASE);
}

/** Demo data for Bangkok locations when backend is not available */
const DEMO_DATA = {
  "/locations/": {
    data: [
      {
        id: 1,
        name: "Demo Turkish Restaurant",
        lat: 13.7563,
        lng: 100.5018,
        category: "restaurant",
        state: "VERIFIED",
        rating: 4.5,
        confidence_score: 0.95,
        is_turkish: true
      },
      {
        id: 2,
        name: "Demo Turkish Bakery",
        lat: 13.7563,
        lng: 100.5018,
        category: "bakery",
        state: "VERIFIED",
        rating: 4.3,
        confidence_score: 0.90,
        is_turkish: true
      }
    ],
    total: 2
  }
};

/** Kleine helper voor fetch-calls naar onze API */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = 60000
): Promise<T> {
  // Require a configured backend in all modes
  if (!API_BASE) {
    const errorMsg = `Backend not configured: VITE_API_BASE_URL is not set or empty. 
      Current value: "${import.meta.env.VITE_API_BASE_URL || 'undefined'}"
      Please set VITE_API_BASE_URL environment variable before building.`;
    console.error('[apiFetch]', errorMsg);
    throw new Error(errorMsg);
  }

  const url = `${API_BASE}${path}`;
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug("[apiFetch] →", url, init?.method || "GET");
  }

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Simple retry/backoff for cold starts or transient failures
    const maxAttempts = 3;
    const delays = [500, 1500]; // ms between attempts (after first failure)

    let lastError: unknown = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        // Automatically add X-Client-Id header for anonymous user tracking
        const clientId = getOrCreateClientId();

        // Merge headers correctly: start with init.headers (if it's an object), then add our defaults
        // This ensures X-Client-Id is always included and not overwritten
        const initHeaders = init?.headers instanceof Headers
          ? Object.fromEntries(init.headers.entries())
          : (init?.headers ?? {});

        const headers = {
          "Content-Type": "application/json",
          "X-Client-Id": clientId,
          ...initHeaders,
        };

        // Use timeout controller signal (will override init.signal if provided)
        // This ensures timeout always works even if caller provides their own signal
        const res = await fetch(url, {
          ...init,
          headers,
          signal: controller.signal,
        });
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.debug("[apiFetch] status", res.status, "for", url);
        }

        if (!res.ok) {
          if (res.status === 401 || res.status === 403) {
            if (import.meta.env.DEV) {
              // eslint-disable-next-line no-console
              console.warn("[apiFetch] auth rejected", res.status, url);
            }
            // Whitelist of endpoints where 401/403 is expected and should not trigger signOut
            // These are typically optional endpoints that may return 401 for unauthenticated users
            const optionalAuthEndpoints = [
              "/api/v1/users/me", // All /me endpoints are optional or may return 401 for unauthenticated users
            ];
            const isOptionalEndpoint = optionalAuthEndpoints.some(endpoint => path.startsWith(endpoint));
            
            // Only sign out for admin endpoints or non-optional endpoints
            // and only on the final retry attempt to avoid signing out during
            // temporary token refresh issues or network errors
            if (!isOptionalEndpoint && attempt === maxAttempts) {
              const { data: { session } } = await supabase.auth.getSession();
              // Only sign out if we still have a session - this means the token
              // was rejected by the backend, not that we're already logged out
              if (session) {
                try { await supabase.auth.signOut(); } catch { }
              }
            }
            throw new Error(`AUTH_${res.status} ${url}`);
          }
          // Retry on typical warm-up statuses
          if (res.status === 502 || res.status === 503 || res.status === 504) {
            const text = await res.text().catch(() => "");
            lastError = new Error(
              `API ${res.status} ${res.statusText} @ ${path}${text ? ` — ${text.slice(0, 300)}` : ""}`
            );
            // fall through to retry logic
          } else {
            const text = await res.text().catch(() => "");
            throw new Error(
              `API ${res.status} ${res.statusText} @ ${path}${text ? ` — ${text.slice(0, 300)}` : ""}`
            );
          }
        } else {
          // Alleen JSON is geldig; non-JSON behandelen als fout (bv. warm-up HTML)
          const ct = res.headers.get("content-type") || "";
          if (!ct.includes("application/json")) {
            throw new Error(`Invalid response content-type for ${path}: ${ct || "<none>"} @ ${url}`);
          }
          return (await res.json()) as T;
        }
      } catch (err) {
        // Check if aborted (timeout)
        if (err instanceof Error && err.name === 'AbortError' && controller.signal.aborted) {
          throw new Error(`Request timeout after ${timeoutMs}ms: ${path}`);
        }
        // Network/CORS/etc.
        lastError = err;

        // Don't retry if aborted (timeout)
        if (controller.signal.aborted) {
          break;
        }
      }

      if (attempt < maxAttempts && !controller.signal.aborted) {
        const wait = delays[attempt - 1] ?? 1500;
        await new Promise((r) => setTimeout(r, wait));
      }
    }

    // Development-only demo fallback to keep local UI usable when backend missing
    if (import.meta.env.DEV) {
      const demoResponse = DEMO_DATA[path as keyof typeof DEMO_DATA];
      if (demoResponse) return demoResponse as T;
    }

    throw (lastError ?? new Error('Failed to fetch API'));
  } finally {
    clearTimeout(timeoutId);
  }
}

/** Admin-key uit localStorage ophalen (niet bundelen) */
export function getAdminKey(): string {
  return localStorage.getItem("ADMIN_API_KEY") || "";
}

/**
 * Get or create a client ID (UUID) stored in localStorage.
 * Used for anonymous user tracking.
 */
export function getOrCreateClientId(): string {
  const STORAGE_KEY = "TDA_CLIENT_ID";
  let clientId = localStorage.getItem(STORAGE_KEY);

  if (!clientId) {
    // Generate a UUID v4
    clientId = crypto.randomUUID?.() ||
      `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
    localStorage.setItem(STORAGE_KEY, clientId);
  }

  return clientId;
}

export async function authFetch<T>(
  path: string,
  init?: RequestInit,
  timeoutMs?: number
): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not authenticated");
  if (import.meta.env.DEV) {
    // Helpful during local debugging
    // eslint-disable-next-line no-console
    console.debug("authFetch →", `${API_BASE}${path}`);
  }
  try {
    return await apiFetch<T>(
      path,
      {
        ...init,
        headers: {
          ...(init?.headers ?? {}),
          Authorization: `Bearer ${token}`,
        },
      },
      timeoutMs
    );
  } catch (err: any) {
    if (typeof err?.message === "string" && err.message.startsWith("AUTH_")) {
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.error("[authFetch] admin auth failed", err);
      }
      toast.error("Not authorized as admin (401/403).");
    }
    throw err;
  }
}

/**
 * API fetch with optional authentication.
 * Adds Authorization header if user is authenticated, otherwise works like apiFetch.
 * Use this for endpoints that support both authenticated and anonymous users.
 */
export async function apiFetchWithOptionalAuth<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = 60000
): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  
  const headers = {
    ...(init?.headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  
  return apiFetch<T>(path, { ...init, headers }, timeoutMs);
}

/**
 * Track click on outreach email link.
 * Called when user opens mapview from an outreach email.
 */
export async function trackOutreachClick(emailId: number): Promise<{ ok: boolean; message: string }> {
  return apiFetch<{ ok: boolean; message: string }>(
    `/api/v1/outreach/track-click?email_id=${emailId}`,
    {
      method: "POST",
    }
  );
}

export async function whoAmI(): Promise<{ ok: boolean; admin_email: string }> {
  return authFetch("/api/v1/admin/whoami");
}

// Cities Overview types
export interface CityReadiness {
  city_key: string;
  city_name: string;
  has_districts: boolean;
  districts_count: number;
  verified_count: number;
  candidate_count: number;
  coverage_ratio: number;
  growth_weekly: number | null;
  readiness_status: "active" | "configured_inactive" | "config_incomplete";
  readiness_notes: string | null;
}

export interface CitiesOverview {
  cities: CityReadiness[];
}

export async function getCitiesOverview(): Promise<CitiesOverview> {
  return authFetch("/api/v1/admin/cities");
}

// AI Config types
export interface AIConfig {
  id: number;
  classify_min_conf: number;
  verify_min_conf: number;
  task_verifier_min_conf: number;
  auto_promote_conf: number;
  monitor_low_conf_days: number;
  monitor_medium_conf_days: number;
  monitor_high_conf_days: number;
  monitor_verified_few_reviews_days: number;
  monitor_verified_medium_reviews_days: number;
  monitor_verified_many_reviews_days: number;
  updated_at: string;
  updated_by: string | null;
}

export interface AIConfigUpdate {
  classify_min_conf?: number;
  verify_min_conf?: number;
  task_verifier_min_conf?: number;
  auto_promote_conf?: number;
  monitor_low_conf_days?: number;
  monitor_medium_conf_days?: number;
  monitor_high_conf_days?: number;
  monitor_verified_few_reviews_days?: number;
  monitor_verified_medium_reviews_days?: number;
  monitor_verified_many_reviews_days?: number;
}

export async function getAIConfig(): Promise<AIConfig> {
  return authFetch<AIConfig>("/api/v1/admin/ai/config");
}

export async function updateAIConfig(update: AIConfigUpdate): Promise<AIConfig> {
  return authFetch<AIConfig>("/api/v1/admin/ai/config", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(update),
  });
}

// --- Metrics ---
export interface WorkerStatus {
  id: string;
  label: string;
  lastRun: string | null;
  durationSeconds: number | null;
  processedCount: number | null;
  errorCount: number | null;
  status: "ok" | "warning" | "error" | "unknown";
  windowLabel?: string | null;
  quotaInfo?: Record<string, number | null> | null;
  notes?: string | null;
  diagnosisCode?: string | null;
  workerType?: "queue_based" | "direct" | "legacy" | null;
}

export interface WorkerRun {
  id: string;
  bot: string;
  city?: string | null;
  category?: string | null;
  status: string;
  progress: number;
  startedAt?: string | null;
}

export interface CityProgressData {
  verifiedCount: number;
  candidateCount: number;
  coverageRatio: number;
  growthWeekly: number;
}

export interface CityProgress {
  // Multi-city support: cities dict with city keys
  cities: Record<string, CityProgressData>;
  // Backward compatibility: direct rotterdam accessor
  rotterdam?: CityProgressData;
}

export interface QualityMetrics {
  conversionRateVerified14d: number;
  taskErrorRate60m: number;
  google429Last60m: number;
}

export interface DiscoveryMetrics {
  newCandidatesPerWeek: number;
}

// --- Category Health Metrics ---
export interface CategoryHealth {
  overpassCalls: number;
  overpassSuccessfulCalls: number;
  overpassZeroResults: number;
  overpassZeroResultRatioPct: number;
  insertedLocationsLast7d: number;
  stateCounts: Record<string, number>;
  avgConfidenceLast7d: number | null;
  aiClassificationsLast7d: number;
  aiActionKeep: number;
  aiActionIgnore: number;
  aiAvgConfidence: number | null;
  promotedVerifiedLast7d: number;
  // New fields for Turkish-first strategy metrics
  overpassFound: number;
  turkishCoverageRatioPct: number;
  aiPrecisionPct: number;
  status: "healthy" | "warning" | "degraded" | "critical" | "no_data";
}

export interface CategoryHealthResponse {
  categories: Record<string, CategoryHealth>;
  timeWindows: {
    overpassWindowHours: number;
    insertsWindowDays: number;
    classificationsWindowDays: number;
    promotionsWindowDays: number;
  };
}

// --- Discovery Grid ---
export interface DiscoveryGridCell {
  latCenter: number;
  lngCenter: number;
  calls: number;
  inserts: number;
  error429: number;
  errorOther: number;
  district: string | null;
}

export interface DiscoveryCoverageCell {
  latCenter: number;
  lngCenter: number;
  district: string | null;
  totalCalls: number;
  visitCount: number;
  successfulCalls: number;
  error429: number;
  errorOther: number;
  firstSeenAt: string | null;
  lastSeenAt: string | null;
}

export async function getDiscoveryGrid(
  city?: string,
  district?: string,
  category?: string
): Promise<DiscoveryGridCell[]> {
  const params = new URLSearchParams();
  if (city) params.set("city", city);
  if (district) params.set("district", district);
  if (category) params.set("category", category);
  const query = params.toString();
  const raw = await authFetch<
    Array<{
      lat_center: number;
      lng_center: number;
      calls: number;
      inserts: number;
      error_429: number;
      error_other: number;
      district: string | null;
    }>
  >(`/api/v1/admin/discovery/grid${query ? `?${query}` : ""}`, undefined, 60000);
  return raw.map((cell) => ({
    latCenter: cell.lat_center,
    lngCenter: cell.lng_center,
    calls: cell.calls,
    inserts: cell.inserts,
    error429: cell.error_429,
    errorOther: cell.error_other,
    district: cell.district,
  }));
}

export async function getDiscoveryCoverage(
  city: string,
  district?: string,
  from?: string,
  to?: string,
  category?: string
): Promise<DiscoveryCoverageCell[]> {
  const params = new URLSearchParams();
  params.set("city", city);
  if (district) params.set("district", district);
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  if (category) params.set("category", category);

  const raw = await authFetch<
    Array<{
      lat_center: number;
      lng_center: number;
      district: string | null;
      total_calls: number;
      visit_count: number;
      successful_calls: number;
      error_429: number;
      error_other: number;
      first_seen_at: string | null;
      last_seen_at: string | null;
    }>
  >(`/api/v1/admin/discovery/coverage?${params.toString()}`, undefined, 60000);

  return raw.map((cell) => ({
    latCenter: cell.lat_center,
    lngCenter: cell.lng_center,
    district: cell.district,
    totalCalls: cell.total_calls,
    visitCount: cell.visit_count,
    successfulCalls: cell.successful_calls,
    error429: cell.error_429,
    errorOther: cell.error_other,
    firstSeenAt: cell.first_seen_at,
    lastSeenAt: cell.last_seen_at,
  }));
}

// Unified coverage summary for admin summary widget
export interface DiscoveryCoverageSummary {
  visitedCells: number;
  totalCells: number;
  coverageRatio: number;
  totalCalls: number;
  errorRate: number;
  totalInserts30d: number;
}

export async function getDiscoveryCoverageSummary(
  city: string,
  district?: string,
  from?: string,
  to?: string
): Promise<DiscoveryCoverageSummary> {
  const params = new URLSearchParams();
  params.set("city", city);
  if (district) params.set("district", district);
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  return authFetch<DiscoveryCoverageSummary>(
    `/api/v1/admin/discovery/summary?${params.toString()}`,
    undefined,
    60000
  );
}

export async function getCityDistricts(city: string): Promise<string[]> {
  const res = await authFetch<{ districts: string[] }>(
    `/api/v1/admin/discovery/districts?city=${city}`
  );
  return res.districts ?? [];
}

export interface LatencyMetrics {
  p50Ms: number;
  avgMs: number;
  maxMs: number;
}

export interface WeeklyCandidatesItem {
  weekStart: string;
  count: number;
}

export interface StaleCandidatesMetrics {
  totalStale: number;
  bySource: Record<string, number>;
  byCity: Record<string, number>;
  daysThreshold: number;
}

export interface MetricsSnapshot {
  cityProgress: CityProgress;
  quality: QualityMetrics | null;
  discovery: DiscoveryMetrics | null;
  latency: LatencyMetrics | null;
  weeklyCandidates?: WeeklyCandidatesItem[] | null;
  workers: WorkerStatus[];
  currentRuns: WorkerRun[];
  staleCandidates?: StaleCandidatesMetrics | null;
}

type RawWorkerStatus = {
  id: string;
  label: string;
  last_run: string | null;
  duration_seconds: number | null;
  processed_count: number | null;
  error_count: number | null;
  status: "ok" | "warning" | "error" | "unknown";
  window_label?: string | null;
  quota_info?: Record<string, number | null> | null;
  notes?: string | null;
  diagnosis_code?: string | null;
  worker_type?: "queue_based" | "direct" | "legacy" | null;
};

type RawWorkerRun = {
  id: string;
  bot: string;
  city?: string | null;
  category?: string | null;
  status: string;
  progress: number;
  started_at?: string | null;
};

type RawCityProgressData = {
  verified_count: number;
  candidate_count: number;
  coverage_ratio: number;
  growth_weekly: number;
};

type RawMetricsSnapshot = {
  city_progress: {
    cities?: Record<string, RawCityProgressData>;
    rotterdam?: RawCityProgressData; // Backward compatibility
  };
  quality: {
    conversion_rate_verified_14d: number;
    task_error_rate_60m: number;
    google429_last60m: number;
  } | null;
  discovery: {
    new_candidates_per_week: number;
  } | null;
  latency: {
    p50_ms: number;
    avg_ms: number;
    max_ms: number;
  } | null;
  weekly_candidates?: { week_start: string; count: number }[] | null;
  workers: RawWorkerStatus[];
  current_runs: RawWorkerRun[];
  stale_candidates?: {
    total_stale: number;
    by_source: Record<string, number>;
    by_city: Record<string, number>;
    days_threshold: number;
  } | null;
};

function normalizeWorkerStatus(raw: RawWorkerStatus): WorkerStatus {
  return {
    id: raw.id,
    label: raw.label,
    lastRun: raw.last_run,
    durationSeconds: raw.duration_seconds,
    processedCount: raw.processed_count,
    errorCount: raw.error_count,
    status: raw.status,
    windowLabel: raw.window_label,
    quotaInfo: raw.quota_info ?? null,
    notes: raw.notes ?? null,
    diagnosisCode: raw.diagnosis_code ?? null,
    workerType: raw.worker_type ?? null,
  };
}

function normalizeWorkerRun(raw: RawWorkerRun): WorkerRun {
  return {
    id: raw.id,
    bot: raw.bot,
    city: raw.city ?? null,
    category: raw.category ?? null,
    status: raw.status,
    progress: raw.progress,
    startedAt: raw.started_at ?? null,
  };
}

function normalizeCityProgress(raw: {
  cities?: Record<string, RawCityProgressData>;
  rotterdam?: RawCityProgressData;
}): CityProgress {
  const cities: Record<string, CityProgressData> = {};

  // Handle new multi-city structure
  if (raw.cities) {
    for (const [cityKey, cityData] of Object.entries(raw.cities)) {
      cities[cityKey] = {
        verifiedCount: cityData.verified_count,
        candidateCount: cityData.candidate_count,
        coverageRatio: cityData.coverage_ratio,
        growthWeekly: cityData.growth_weekly,
      };
    }
  }

  // Handle backward compatibility: rotterdam as direct field
  if (raw.rotterdam && !cities.rotterdam) {
    cities.rotterdam = {
      verifiedCount: raw.rotterdam.verified_count,
      candidateCount: raw.rotterdam.candidate_count,
      coverageRatio: raw.rotterdam.coverage_ratio,
      growthWeekly: raw.rotterdam.growth_weekly,
    };
  }

  return {
    cities,
    rotterdam: cities.rotterdam, // Backward compatibility accessor
  };
}

function normalizeMetricsSnapshot(raw: RawMetricsSnapshot): MetricsSnapshot {
  return {
    cityProgress: normalizeCityProgress(raw.city_progress),
    quality: raw.quality
      ? {
        conversionRateVerified14d: raw.quality.conversion_rate_verified_14d,
        taskErrorRate60m: raw.quality.task_error_rate_60m,
        google429Last60m: raw.quality.google429_last60m,
      }
      : null,
    discovery: raw.discovery
      ? { newCandidatesPerWeek: raw.discovery.new_candidates_per_week }
      : null,
    latency: raw.latency
      ? {
        p50Ms: raw.latency.p50_ms,
        avgMs: raw.latency.avg_ms,
        maxMs: raw.latency.max_ms,
      }
      : null,
    weeklyCandidates: raw.weekly_candidates
      ? raw.weekly_candidates.map((item) => ({
        weekStart: item.week_start,
        count: item.count,
      }))
      : [],
    workers: (raw.workers ?? []).map(normalizeWorkerStatus),
    currentRuns: (raw.current_runs ?? []).map(normalizeWorkerRun),
    staleCandidates: raw.stale_candidates
      ? {
        totalStale: raw.stale_candidates.total_stale,
        bySource: raw.stale_candidates.by_source ?? {},
        byCity: raw.stale_candidates.by_city ?? {},
        daysThreshold: raw.stale_candidates.days_threshold,
      }
      : null,
  };
}

export async function getCategoryHealthMetrics(): Promise<CategoryHealthResponse> {
  const raw = await authFetch<{
    categories: Record<
      string,
      {
        overpass_calls: number;
        overpass_successful_calls: number;
        overpass_zero_results: number;
        overpass_zero_result_ratio_pct: number;
        inserted_locations_last_7d: number;
        state_counts: Record<string, number>;
        avg_confidence_last_7d: number | null;
        ai_classifications_last_7d: number;
        ai_action_keep: number;
        ai_action_ignore: number;
        ai_avg_confidence: number | null;
        promoted_verified_last_7d: number;
        overpass_found: number;
        turkish_coverage_ratio_pct: number;
        ai_precision_pct: number;
        status: "healthy" | "warning" | "degraded" | "critical" | "no_data";
      }
    >;
    time_windows: {
      overpass_window_hours: number;
      inserts_window_days: number;
      classifications_window_days: number;
      promotions_window_days: number;
    };
  }>("/api/v1/admin/metrics/categories");

  // Transform snake_case to camelCase
  const categories: Record<string, CategoryHealth> = {};
  for (const [key, value] of Object.entries(raw.categories)) {
    categories[key] = {
      overpassCalls: value.overpass_calls,
      overpassSuccessfulCalls: value.overpass_successful_calls,
      overpassZeroResults: value.overpass_zero_results,
      overpassZeroResultRatioPct: value.overpass_zero_result_ratio_pct,
      insertedLocationsLast7d: value.inserted_locations_last_7d,
      stateCounts: value.state_counts,
      avgConfidenceLast7d: value.avg_confidence_last_7d,
      aiClassificationsLast7d: value.ai_classifications_last_7d,
      aiActionKeep: value.ai_action_keep,
      aiActionIgnore: value.ai_action_ignore,
      aiAvgConfidence: value.ai_avg_confidence,
      promotedVerifiedLast7d: value.promoted_verified_last_7d,
      overpassFound: value.overpass_found,
      turkishCoverageRatioPct: value.turkish_coverage_ratio_pct,
      aiPrecisionPct: value.ai_precision_pct,
      status: value.status,
    };
  }

  return {
    categories,
    timeWindows: {
      overpassWindowHours: raw.time_windows.overpass_window_hours,
      insertsWindowDays: raw.time_windows.inserts_window_days,
      classificationsWindowDays: raw.time_windows.classifications_window_days,
      promotionsWindowDays: raw.time_windows.promotions_window_days,
    },
  };
}

export async function getMetricsSnapshot(): Promise<MetricsSnapshot> {
  // Use longer timeout (120 seconds) for metrics snapshot due to complex queries
  // This endpoint aggregates data from multiple tables and can take longer,
  // especially during active discovery runs
  const raw = await authFetch<RawMetricsSnapshot>(
    "/api/v1/admin/metrics/snapshot",
    undefined,
    120000 // 120 seconds timeout
  );
  return normalizeMetricsSnapshot(raw);
}

export interface DiscoveryKPIDaily {
  day: string;
  inserted: number;
  deduped_fuzzy: number;
  updated_existing: number;
  deduped_place_id: number;
  discovered: number;
  failed: number;
}

export interface DiscoveryKPIs {
  days: number;
  daily: DiscoveryKPIDaily[];
  totals: {
    inserted: number;
    deduped_fuzzy: number;
    updated_existing: number;
    deduped_place_id: number;
    discovered: number;
    failed: number;
  };
}

export async function getDiscoveryKPIs(days: number = 30): Promise<DiscoveryKPIs> {
  return authFetch<DiscoveryKPIs>(`/api/v1/admin/discovery/kpis?days=${days}`);
}

// ============================================================================
// Polls API (User-facing)
// ============================================================================

export interface PollOption {
  id: number;
  option_text: string;
  display_order: number;
}

export interface Poll {
  id: number;
  title: string;
  question: string;
  poll_type: "single_choice" | "multi_choice";
  options: PollOption[];
  is_sponsored: boolean;
  starts_at: string;
  ends_at: string | null;
  user_has_responded: boolean;
}

export interface PollStats {
  poll_id: number;
  total_responses: number;
  option_counts: Record<number, number>;
  privacy_threshold_met: boolean;
}

/**
 * List active polls (optionally filtered by city).
 */
export async function listPolls(cityKey?: string, limit: number = 10): Promise<Poll[]> {
  const params = new URLSearchParams();
  if (cityKey) params.set("city_key", cityKey);
  params.set("limit", limit.toString());

  return apiFetch<Poll[]>(`/api/v1/polls?${params.toString()}`);
}

/**
 * Get a single poll by ID.
 */
export async function getPoll(pollId: number): Promise<Poll> {
  return apiFetch<Poll>(`/api/v1/polls/${pollId}`);
}

/**
 * Get a single location by ID.
 */
export async function getLocationById(locationId: number): Promise<LocationMarker> {
  return apiFetch<LocationMarker>(`/api/v1/locations/${locationId}`);
}

/**
 * Submit a poll response.
 */
export async function submitPollResponse(pollId: number, optionId: number): Promise<{ ok: boolean; response_id: number }> {
  return apiFetchWithOptionalAuth<{ ok: boolean; response_id: number }>(
    `/api/v1/polls/${pollId}/responses`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ option_id: optionId }),
    }
  );
}

/**
 * Get poll statistics (only shown if privacy threshold is met).
 */
export async function getPollStats(pollId: number): Promise<PollStats> {
  return apiFetch<PollStats>(`/api/v1/polls/${pollId}/stats`);
}

// ============================================================================
// Activity Feed API
// ============================================================================

export interface ActivityItem {
  is_promoted?: boolean;
  id: number;
  activity_type: "check_in" | "reaction" | "note" | "poll_response" | "favorite" | "bulletin_post" | "event";
  location_id: number | null;
  location_name: string | null;
  payload: Record<string, any>;
  created_at: string;
  media_url?: string | null;
  user?: {
    id: string;
    name: string | null;
    avatar_url: string | null;
    primary_role?: string | null;
    secondary_role?: string | null;
  } | null;
  like_count: number;
  is_liked: boolean;
  is_bookmarked: boolean;
  reactions?: Record<ReactionType, number> | null;
  user_reaction?: ReactionType | null;
  labels?: string[] | null;
}

/**
 * Get activity feed for current user/client.
 * @param limit Maximum number of items to return
 * @param offset Number of items to skip
 * @param activityType Optional filter by activity type (check_in, reaction, note, poll_response, favorite)
 */
export async function getActivityFeed(
  limit: number = 50,
  offset: number = 0,
  activityType?: ActivityItem["activity_type"]
): Promise<ActivityItem[]> {
  const clientId = getOrCreateClientId();
  const params = new URLSearchParams();
  params.set("limit", limit.toString());
  params.set("offset", offset.toString());
  if (activityType) {
    params.set("activity_type", activityType);
  }

  return apiFetch<ActivityItem[]>(
    `/api/v1/activity?${params.toString()}`,
    {
      headers: {
        "X-Client-Id": clientId,
      },
    }
  );
}

/**
 * Toggle like on an activity item.
 */
export async function toggleActivityLike(activityId: number): Promise<{ liked: boolean; like_count: number }> {
  return apiFetchWithOptionalAuth<{ liked: boolean; like_count: number }>(
    `/api/v1/activity/${activityId}/like`,
    {
      method: "POST",
    }
  );
}

/**
 * Toggle bookmark on an activity item.
 */
export async function toggleActivityBookmark(activityId: number): Promise<{ bookmarked: boolean }> {
  return apiFetchWithOptionalAuth<{ bookmarked: boolean }>(
    `/api/v1/activity/${activityId}/bookmark`,
    {
      method: "POST",
    }
  );
}

/**
 * Toggle emoji reaction on an activity item.
 */
export async function toggleActivityReaction(
  activityId: number,
  reactionType: ReactionType
): Promise<{ reaction_type: ReactionType; is_active: boolean; count: number }> {
  return apiFetchWithOptionalAuth<{ reaction_type: ReactionType; is_active: boolean; count: number }>(
    `/api/v1/activity/${activityId}/reactions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reaction_type: reactionType }),
    }
  );
}

/**
 * Get reaction counts for an activity item.
 */
export async function getActivityReactions(
  activityId: number
): Promise<{ reactions: Record<ReactionType, number> }> {
  return apiFetch<{ reactions: Record<ReactionType, number> }>(
    `/api/v1/activity/${activityId}/reactions`
  );
}

// ============================================================================
// User Profile API
// ============================================================================

export interface CurrentUser {
  name: string | null;
  avatar_url: string | null;
}

export interface UserProfile {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  city_key: string | null;
  language_pref: string;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Get current user profile (name and avatar).
 * Returns null for anonymous users or if request fails.
 */
export async function getWeekFeedback(): Promise<{
  should_show: boolean;
  message: string;
  week_start: string;
}> {
  // This endpoint requires authentication
  return authFetch<{
    should_show: boolean;
    message: string;
    week_start: string;
  }>("/api/v1/users/me/week-feedback");
}

export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    // Use apiFetchWithOptionalAuth to include Authorization header if available
    return await apiFetchWithOptionalAuth<CurrentUser>(`/api/v1/users/me`);
  } catch (error) {
    // Return null for anonymous users or errors
    return null;
  }
}

/**
 * Check if username is available (case-insensitive).
 */
export async function checkUsernameAvailable(username: string): Promise<{ available: boolean }> {
  return authFetch<{ available: boolean }>(
    `/api/v1/users/me/check-username?username=${encodeURIComponent(username)}`
  );
}

/**
 * Update user profile (display_name and/or avatar_url).
 */
export async function updateProfile(data: {
  display_name?: string;
  avatar_url?: string;
}): Promise<UserProfile> {
  return authFetch<UserProfile>("/api/v1/users/me/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export interface UsernameChangeStatus {
  can_change: boolean;
  last_change: string | null;
  next_change_available: string | null;
  days_remaining: number;
}

/**
 * Get username change status (1x per month limit check).
 */
export async function getUsernameChangeStatus(): Promise<UsernameChangeStatus> {
  return authFetch<UsernameChangeStatus>("/api/v1/users/me/username-change-status");
}

// ============================================================================
// Onboarding API
// ============================================================================

export interface OnboardingStatus {
  first_run: boolean;
  onboarding_completed: boolean;
  onboarding_version: string | null;
}

export interface OnboardingData {
  home_city: string;
  home_region?: string | null;
  home_city_key?: string | null;  // CityKey for news preferences
  memleket?: string[] | null;
  gender?: "male" | "female" | "prefer_not_to_say" | null;
}

export interface OnboardingCompleteResponse {
  success: boolean;
  xp_awarded: number;
  badge_earned: string | null;
}

export interface OnboardingResult {
  success: boolean;
  xp_awarded: number;
  badge_earned: string | null;
}

const ONBOARDING_STORAGE_KEY = "tda_onboarding_completed";
const ONBOARDING_VERSION_KEY = "tda_onboarding_version";

/**
 * Get onboarding status for current user (from localStorage).
 * Onboarding is device-specific, not account-specific.
 */
export function getOnboardingStatus(): OnboardingStatus {
  const completed = localStorage.getItem(ONBOARDING_STORAGE_KEY) === "true";
  const version = localStorage.getItem(ONBOARDING_VERSION_KEY) || null;

  return {
    first_run: !completed,
    onboarding_completed: completed,
    onboarding_version: version,
  };
}

/**
 * Complete onboarding flow (saves to backend API and localStorage).
 * Onboarding is device-specific for anonymous users (client_id), account-specific for authenticated users.
 */
export async function completeOnboarding(data: OnboardingData): Promise<OnboardingResult> {
  // Try to save to backend API first
  try {
    const response = await apiFetchWithOptionalAuth<OnboardingCompleteResponse>(
      "/api/v1/users/me/onboarding/complete",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          home_city: data.home_city,
          home_region: data.home_region || null,
          home_city_key: data.home_city_key || null,
          memleket: data.memleket || null,
          gender: data.gender || null,
        }),
      }
    );

    // On success, also save to localStorage for backwards compatibility
    localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");
    localStorage.setItem(ONBOARDING_VERSION_KEY, "v1.0");
    localStorage.setItem("tda_onboarding_data", JSON.stringify(data));

    return {
      success: response.success,
      xp_awarded: response.xp_awarded,
      badge_earned: response.badge_earned,
    };
  } catch (error) {
    // Fallback to localStorage if API call fails
    console.warn("Failed to save onboarding to backend, using localStorage fallback:", error);

    localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");
    localStorage.setItem(ONBOARDING_VERSION_KEY, "v1.0");
    localStorage.setItem("tda_onboarding_data", JSON.stringify(data));

    return {
      success: true,
      xp_awarded: 0, // No XP/badge for localStorage-based onboarding
      badge_earned: null,
    };
  }
}

/**
 * Reset onboarding flow (clears localStorage).
 * Useful for testing or allowing users to restart onboarding.
 */
export function resetOnboarding(): void {
  localStorage.removeItem(ONBOARDING_STORAGE_KEY);
  localStorage.removeItem(ONBOARDING_VERSION_KEY);
  localStorage.removeItem("tda_onboarding_data");
}

// ============================================================================
// Location Interactions API (Check-ins, Reactions, Notes, Favorites)
// ============================================================================

// Check-ins
export interface CheckInStats {
  location_id: number;
  total_check_ins: number;
  check_ins_today: number;
  unique_users_today: number;
  check_ins_this_week?: number;
  status_text?: string;
}

/**
 * Create a check-in for a location.
 */
export async function createCheckIn(locationId: number): Promise<{ ok: boolean; check_in_id: number }> {
  return apiFetchWithOptionalAuth<{ ok: boolean; check_in_id: number }>(
    `/api/v1/locations/${locationId}/check-ins`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}), // Send empty JSON body to satisfy FastAPI
    }
  );
}

/**
 * Get check-in statistics for a location.
 */
export async function getCheckInStats(locationId: number): Promise<CheckInStats> {
  return apiFetch<CheckInStats>(`/api/v1/locations/${locationId}/check-ins`);
}

// Mahallelisi
export interface MahallelisiResponse {
  user_id: string;
  name: string;
  check_in_count: number;
  primary_role?: string;
  secondary_role?: string;
}

/**
 * Get the most active user (Mahallelisi) for a location this week.
 */
export async function getLocationMahallelisi(
  locationId: number
): Promise<MahallelisiResponse | null> {
  return apiFetch<MahallelisiResponse | null>(
    `/api/v1/locations/${locationId}/mahallelisi`
  );
}

// Reactions
export interface ReactionStats {
  location_id: number;
  reactions: Record<string, number>;
  user_reaction?: ReactionType | null;
}

export type ReactionType = string; // Custom emoji string

/**
 * Toggle a reaction on a location (add if not exists, remove if exists).
 */
export async function toggleLocationReaction(
  locationId: number,
  reactionType: ReactionType
): Promise<{ reaction_type: ReactionType; is_active: boolean; count: number }> {
  return apiFetchWithOptionalAuth<{ reaction_type: ReactionType; is_active: boolean; count: number }>(
    `/api/v1/locations/${locationId}/reactions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reaction_type: reactionType }),
    }
  );
}

/**
 * Get aggregated reaction counts and user reaction for a location.
 */
export async function getLocationReactions(
  locationId: number
): Promise<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }> {
  return apiFetch<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }>(
    `/api/v1/locations/${locationId}/reactions`
  );
}

/**
 * Toggle a reaction on a news item (add if not exists, remove if exists).
 */
export async function toggleNewsReaction(
  newsId: number,
  reactionType: ReactionType
): Promise<{ reaction_type: ReactionType; is_active: boolean; count: number }> {
  return apiFetchWithOptionalAuth<{ reaction_type: ReactionType; is_active: boolean; count: number }>(
    `/api/v1/news/${newsId}/reactions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reaction_type: reactionType }),
    }
  );
}

/**
 * Get aggregated reaction counts and user reaction for a news item.
 */
export async function getNewsReactions(
  newsId: number
): Promise<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }> {
  return apiFetch<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }>(
    `/api/v1/news/${newsId}/reactions`
  );
}

/**
 * Toggle a reaction on an event (add if not exists, remove if exists).
 */
export async function toggleEventReaction(
  eventId: number,
  reactionType: ReactionType
): Promise<{ reaction_type: ReactionType; is_active: boolean; count: number }> {
  return apiFetchWithOptionalAuth<{ reaction_type: ReactionType; is_active: boolean; count: number }>(
    `/api/v1/events/${eventId}/reactions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reaction_type: reactionType }),
    }
  );
}

/**
 * Get aggregated reaction counts and user reaction for an event.
 */
export async function getEventReactions(
  eventId: number
): Promise<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }> {
  return apiFetch<{ reactions: Record<ReactionType, number>; user_reaction: ReactionType | null }>(
    `/api/v1/events/${eventId}/reactions`
  );
}

// Notes
export interface NoteResponse {
  id: number;
  location_id: number;
  content: string;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
  reaction_count?: number;
  labels?: string[];
}

/**
 * Create a note for a location.
 */
export async function createNote(locationId: number, content: string): Promise<NoteResponse> {
  return apiFetchWithOptionalAuth<NoteResponse>(
    `/api/v1/locations/${locationId}/notes`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    }
  );
}

/**
 * Get notes for a location.
 */
export async function getNotes(
  locationId: number,
  limit: number = 50,
  offset: number = 0,
  sortBy?: string
): Promise<NoteResponse[]> {
  const params = new URLSearchParams();
  params.set("limit", limit.toString());
  params.set("offset", offset.toString());
  if (sortBy) {
    params.set("sort_by", sortBy);
  }
  return apiFetch<NoteResponse[]>(`/api/v1/locations/${locationId}/notes?${params.toString()}`);
}

/**
 * Update a note.
 */
export async function updateNote(noteId: number, content: string): Promise<NoteResponse> {
  return apiFetchWithOptionalAuth<NoteResponse>(
    `/api/v1/locations/notes/${noteId}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    }
  );
}

/**
 * Delete a note.
 */
export async function deleteNote(noteId: number): Promise<{ ok: boolean }> {
  return apiFetchWithOptionalAuth<{ ok: boolean }>(
    `/api/v1/locations/notes/${noteId}`,
    {
      method: "DELETE",
    }
  );
}

// Favorites
/**
 * Add a location to favorites.
 */
export async function addFavorite(locationId: number): Promise<{ ok: boolean; favorite_id: number }> {
  return apiFetchWithOptionalAuth<{ ok: boolean; favorite_id: number }>(
    `/api/v1/locations/${locationId}/favorites`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

/**
 * Remove a location from favorites.
 */
export async function removeFavorite(locationId: number): Promise<{ ok: boolean }> {
  return apiFetchWithOptionalAuth<{ ok: boolean }>(
    `/api/v1/locations/${locationId}/favorites`,
    {
      method: "DELETE",
    }
  );
}

/**
 * Get all favorites for current user/client.
 */
export interface FavoriteItem {
  id: number;
  location_id: number;
  location_name: string | null;
  location_lat: number | null;
  location_lng: number | null;
  created_at: string;
}

export async function getFavorites(limit: number = 50, offset: number = 0): Promise<FavoriteItem[]> {
  const params = new URLSearchParams();
  params.set("limit", limit.toString());
  params.set("offset", offset.toString());
  return apiFetch<FavoriteItem[]>(`/api/v1/favorites?${params.toString()}`);
}

/**
 * Check if a location is in favorites (by checking favorites list).
 */
export async function isFavorite(locationId: number): Promise<boolean> {
  try {
    const favorites = await getFavorites(100, 0);
    return favorites.some((fav) => fav.location_id === locationId);
  } catch {
    return false;
  }
}

// ============================================================================
// Trending Locations API
// ============================================================================

export interface TrendingLocation {
  location_id: number;
  name: string;
  city_key: string;
  category_key?: string | null;
  score: number;
  rank: number;
  check_ins_count: number;
  reactions_count: number;
  notes_count: number;
  has_verified_badge?: boolean;
  is_promoted?: boolean;
}

/**
 * Get trending locations.
 */
export async function getTrendingLocations(
  cityKey?: string,
  categoryKey?: string,
  window: string = "24h",
  limit: number = 20
): Promise<TrendingLocation[]> {
  const params = new URLSearchParams();
  if (cityKey) params.set("city_key", cityKey);
  if (categoryKey) params.set("category_key", categoryKey);
  params.set("window", window);
  params.set("limit", limit.toString());

  return apiFetch<TrendingLocation[]>(`/api/v1/locations/trending?${params.toString()}`);
}

// ============================================================================
// Reports API
// ============================================================================

export interface Report {
  id: number;
  report_type: "location" | "note" | "reaction" | "user";
  target_id: number;
  reason: string;
  details: string | null;
  status: "pending" | "resolved" | "dismissed";
  created_at: string;
}

export interface ReportCreateRequest {
  report_type: "location" | "note" | "reaction" | "user";
  target_id: number;
  reason: string;
  details?: string | null;
}

/**
 * Submit a report.
 */
export async function submitReport(report: ReportCreateRequest): Promise<Report> {
  const clientId = getOrCreateClientId();

  return apiFetch<Report>(
    "/api/v1/reports",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Id": clientId,
      },
      body: JSON.stringify(report),
    }
  );
}

// ============================================================================
// Referrals API
// ============================================================================

export interface ReferralCode {
  code: string;
  uses_count: number;
  created_at: string;
}

export interface ReferralStats {
  total_referrals: number;
  referrals_last_30d: number;
  referral_code: string;
}

export interface ClaimReferralResponse {
  success: boolean;
  referrer_name: string | null;
  message: string;
}

/**
 * Get or create the current user's referral code.
 */
export async function getMyReferralCode(): Promise<ReferralCode> {
  return authFetch<ReferralCode>("/api/v1/referrals/code");
}

/**
 * Get referral statistics for the current user.
 */
export async function getReferralStats(): Promise<ReferralStats> {
  return authFetch<ReferralStats>("/api/v1/referrals/stats");
}

/**
 * Claim a referral code during signup.
 */
export async function claimReferral(code: string): Promise<ClaimReferralResponse> {
  return authFetch<ClaimReferralResponse>(
    "/api/v1/referrals/claim",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ code: code.trim().toUpperCase() }),
    }
  );
}

// ============================================================================
// Privacy Settings API
// ============================================================================

export interface PrivacySettings {
  allow_location_tracking: boolean;
  allow_push_notifications: boolean;
  allow_email_digest: boolean;
  data_retention_consent: boolean;
  updated_at: string | null;
}

export interface PrivacySettingsUpdate {
  allow_location_tracking?: boolean;
  allow_push_notifications?: boolean;
  allow_email_digest?: boolean;
  data_retention_consent?: boolean;
}

/**
 * Get privacy settings for current user/client.
 */
export async function getPrivacySettings(): Promise<PrivacySettings> {
  const clientId = getOrCreateClientId();

  return apiFetch<PrivacySettings>(
    "/api/v1/privacy/settings",
    {
      headers: {
        "X-Client-Id": clientId,
      },
    }
  );
}

/**
 * Update privacy settings (requires authentication).
 */
export async function updatePrivacySettings(update: PrivacySettingsUpdate): Promise<PrivacySettings> {
  const clientId = getOrCreateClientId();

  return authFetch<PrivacySettings>(
    "/api/v1/privacy/settings",
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Id": clientId,
      },
      body: JSON.stringify(update),
    }
  );
}

// ============================================================================
// City Stats API
// ============================================================================

export interface CityStats {
  city_key: string;
  check_ins_count: number;
  reactions_count: number;
  notes_count: number;
  favorites_count: number;
  poll_responses_count: number;
  trending_locations_count: number;
  unique_locations_count: number;
  total_activity: number;
  window_days: number;
}

/**
 * Get statistics for a specific city.
 */
export async function getCityStats(cityKey: string, windowDays: number = 7): Promise<CityStats> {
  return apiFetch<CityStats>(
    `/api/v1/stats/cities/${cityKey}?window_days=${windowDays}`
  );
}

// ============================================================================
// Business Analytics API
// ============================================================================

export interface BusinessAnalyticsOverview {
  total_locations: number;
  approved_locations: number;
  total_views: number;
  total_check_ins: number;
  total_reactions: number;
  total_notes: number;
  total_favorites: number;
  trending_locations: number;
  period_days: number;
}

export interface LocationAnalytics {
  location_id: number;
  views: number;
  check_ins: number;
  reactions: number;
  notes: number;
  favorites: number;
  trending_score: number | null;
  is_trending: boolean;
  period_days: number;
}

export interface EngagementMetrics {
  total_engagement: number;
  engagement_rate: number;
  top_locations: Array<{ location_id: number; engagement_count: number }>;
  activity_timeline: Array<{ date: string; count: number }>;
}

export interface TrendingMetrics {
  trending_locations: Array<{
    location_id: number;
    trending_score: number;
    created_at: string;
  }>;
  trending_scores: number[];
}

export async function getBusinessAnalyticsOverview(periodDays: number = 7): Promise<BusinessAnalyticsOverview> {
  return authFetch<BusinessAnalyticsOverview>(
    `/api/v1/business/analytics/overview?period_days=${periodDays}`
  );
}

export async function getLocationAnalytics(locationId: number, periodDays: number = 7): Promise<LocationAnalytics> {
  return authFetch<LocationAnalytics>(
    `/api/v1/business/analytics/locations/${locationId}?period_days=${periodDays}`
  );
}

export async function getEngagementMetrics(periodDays: number = 7): Promise<EngagementMetrics> {
  return authFetch<EngagementMetrics>(
    `/api/v1/business/analytics/engagement?period_days=${periodDays}`
  );
}

export async function getTrendingMetrics(): Promise<TrendingMetrics> {
  return authFetch<TrendingMetrics>("/api/v1/business/analytics/trending");
}

// ============================================================================
// Premium Features API
// ============================================================================

export interface SubscriptionStatus {
  tier: string;
  status: string;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  enabled_features: string[];
}

export interface FeaturesResponse {
  tier: string;
  features: string[];
}

export interface SubscribeRequest {
  tier: "premium" | "pro";
  success_url: string;
  cancel_url: string;
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  return authFetch<SubscriptionStatus>("/api/v1/premium/subscription");
}

export async function getFeatures(tier?: string): Promise<FeaturesResponse> {
  const url = tier
    ? `/api/v1/premium/features?tier=${tier}`
    : "/api/v1/premium/features";
  return authFetch<FeaturesResponse>(url);
}

export async function createSubscription(request: SubscribeRequest): Promise<{ session_id: string; url: string }> {
  return authFetch<{ session_id: string; url: string }>(
    "/api/v1/premium/subscribe",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }
  );
}

// ============================================================================
// Google Business Sync API
// ============================================================================

export interface GoogleBusinessConnectResponse {
  oauth_url: string;
  state: string;
}

export interface GoogleBusinessSyncStatus {
  location_id: number;
  sync_status: string;
  last_synced_at: string | null;
  google_business_id: string | null;
  sync_error: string | null;
}

export async function initiateGoogleBusinessConnect(locationId: number): Promise<GoogleBusinessConnectResponse> {
  return authFetch<GoogleBusinessConnectResponse>(
    `/api/v1/google-business/connect?location_id=${locationId}`,
    { method: "POST" }
  );
}

export async function triggerGoogleBusinessSync(locationId: number): Promise<{ success: boolean; location_id: number; synced_at: string }> {
  return authFetch<{ success: boolean; location_id: number; synced_at: string }>(
    `/api/v1/google-business/sync/${locationId}`,
    { method: "POST" }
  );
}

export async function getGoogleBusinessStatus(): Promise<{ locations: GoogleBusinessSyncStatus[] }> {
  return authFetch<{ locations: GoogleBusinessSyncStatus[] }>("/api/v1/google-business/status");
}

// ============================================================================
// User Groups API
// ============================================================================

export interface UserGroup {
  id: number;
  name: string;
  description: string | null;
  created_by: string;
  is_public: boolean;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface GroupMember {
  id: number;
  group_id: number;
  user_id: string;
  role: string;
  joined_at: string;
}

export interface GroupActivity {
  id: number;
  actor_type: string;
  actor_id: string | null;
  activity_type: string;
  location_id: number | null;
  city_key: string | null;
  category_key: string | null;
  payload: Record<string, any> | null;
  created_at: string;
}

export interface GroupCreateRequest {
  name: string;
  description?: string | null;
  is_public?: boolean;
}

export async function createGroup(group: GroupCreateRequest): Promise<UserGroup> {
  return authFetch<UserGroup>(
    "/api/v1/groups",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(group),
    }
  );
}

export async function listGroups(params?: { search?: string; is_public?: boolean; limit?: number; offset?: number }): Promise<UserGroup[]> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.is_public !== undefined) searchParams.set("is_public", String(params.is_public));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const url = searchParams.toString() ? `/api/v1/groups?${searchParams.toString()}` : "/api/v1/groups";
  return authFetch<UserGroup[]>(url);
}

export async function getGroup(groupId: number): Promise<UserGroup> {
  return authFetch<UserGroup>(`/api/v1/groups/${groupId}`);
}

export async function joinGroup(groupId: number): Promise<{ ok: boolean; message: string; membership: GroupMember }> {
  return authFetch<{ ok: boolean; message: string; membership: GroupMember }>(
    `/api/v1/groups/${groupId}/join`,
    { method: "POST" }
  );
}

export async function leaveGroup(groupId: number): Promise<void> {
  return authFetch<void>(
    `/api/v1/groups/${groupId}/leave`,
    { method: "DELETE" }
  );
}

export async function listGroupMembers(groupId: number, limit?: number, offset?: number): Promise<GroupMember[]> {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));

  const url = params.toString() ? `/api/v1/groups/${groupId}/members?${params.toString()}` : `/api/v1/groups/${groupId}/members`;
  return authFetch<GroupMember[]>(url);
}

export async function getGroupActivity(groupId: number, limit?: number, offset?: number): Promise<GroupActivity[]> {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));

  const url = params.toString() ? `/api/v1/groups/${groupId}/activity?${params.toString()}` : `/api/v1/groups/${groupId}/activity`;
  return authFetch<GroupActivity[]>(url);
}

// ============================================================================
// Push Notifications API
// ============================================================================

export interface PushPreferences {
  enabled: boolean;
  poll_notifications: boolean;
  trending_notifications: boolean;
  activity_notifications: boolean;
}

export interface PushPreferencesUpdate {
  enabled?: boolean;
  poll_notifications?: boolean;
  trending_notifications?: boolean;
  activity_notifications?: boolean;
}

export interface DeviceTokenRegister {
  token: string;
  platform?: string;
  user_agent?: string;
}

export async function registerDeviceToken(registration: DeviceTokenRegister): Promise<{ ok: boolean; message: string }> {
  return authFetch<{ ok: boolean; message: string }>(
    "/api/v1/push/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(registration),
    }
  );
}

export async function unregisterDeviceToken(token: string): Promise<{ ok: boolean; message: string }> {
  return authFetch<{ ok: boolean; message: string }>(
    `/api/v1/push/unregister?token=${encodeURIComponent(token)}`,
    { method: "DELETE" }
  );
}

export async function getPushPreferences(): Promise<PushPreferences> {
  return authFetch<PushPreferences>("/api/v1/push/preferences");
}

export async function updatePushPreferences(update: PushPreferencesUpdate): Promise<PushPreferences> {
  return authFetch<PushPreferences>(
    "/api/v1/push/preferences",
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }
  );
}

// ============================================================================
// User Roles & Gamification API
// ============================================================================

export interface UserRolesResponse {
  primary_role: string;
  secondary_role: string | null;
  earned_at: string;
  expires_at: string | null;
  city_key: string | null;
}

export async function getMyRoles(): Promise<UserRolesResponse> {
  return authFetch<UserRolesResponse>("/api/v1/users/me/roles");
}

export interface ActivitySummaryResponse {
  user_id: string;
  last_4_weeks_active_days: number;
  last_activity_date: string | null;
  total_söz_count: number;
  total_check_in_count: number;
  total_poll_response_count: number;
  city_key: string | null;
  updated_at: string;
}

export async function getMyActivitySummary(): Promise<ActivitySummaryResponse> {
  return authFetch<ActivitySummaryResponse>("/api/v1/users/me/activity-summary");
}

export interface NoteSummary {
  id: number;
  location_id: number;
  location_name: string;
  content_preview: string;
  created_at: string;
}

export interface CheckInSummary {
  id: number;
  location_id: number;
  location_name: string;
  created_at: string;
}

export interface ContributionsResponse {
  last_notes: NoteSummary[];
  last_check_ins: CheckInSummary[];
  poll_response_count: number;
}

export async function getMyContributions(): Promise<ContributionsResponse> {
  return authFetch<ContributionsResponse>("/api/v1/users/me/contributions");
}

export interface RecognitionEntry {
  category: string;
  title: string;
  period: string;
  rank: number;
  context: string | null;
}

export interface RecognitionResponse {
  recognitions: RecognitionEntry[];
}

export async function getMyRecognition(): Promise<RecognitionResponse> {
  return authFetch<RecognitionResponse>("/api/v1/users/me/recognition");
}

// ============================================================================
// Leaderboards API
// ============================================================================

export interface LeaderboardUser {
  user_id: string;
  name: string | null;
  role: string | null;
  context: string | null;
}

export interface LeaderboardCard {
  category: string;
  title: string;
  users: LeaderboardUser[];
}

export interface OneCikanlarResponse {
  period: string;
  city_key: string | null;
  cards: LeaderboardCard[];
}

/**
 * Get Öne Çıkanlar (Featured Users) leaderboards.
 */
export async function getOneCikanlar(
  period: "today" | "week" | "month" = "week",
  cityKey?: string | null
): Promise<OneCikanlarResponse> {
  const params = new URLSearchParams();
  params.set("period", period);
  if (cityKey) {
    params.set("city_key", cityKey);
  }
  return apiFetch<OneCikanlarResponse>(`/api/v1/leaderboards/öne-çıkanlar?${params.toString()}`);
}

// ============================================================================
// Rewards API
// ============================================================================

export interface Reward {
  id: number;
  title: string;
  description: string | null;
  reward_type: string;
  sponsor: string;
  status: string;
  claimed_at: string | null;
  created_at: string;
}

export interface UserReward {
  id: number;
  reward: Reward;
  leaderboard_entry_id: number | null;
  status: string;
  claimed_at: string | null;
  created_at: string;
}

export interface ClaimRewardResponse {
  success: boolean;
  reward: Reward | null;
  message: string;
}

/**
 * Get all rewards for the current user.
 */
export async function getMyRewards(status?: string | null): Promise<UserReward[]> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  const query = params.toString();
  return authFetch<UserReward[]>(`/api/v1/rewards/me${query ? `?${query}` : ""}`);
}

/**
 * Get pending (unclaimed) rewards for the current user.
 */
export async function getMyPendingRewards(): Promise<UserReward[]> {
  return authFetch<UserReward[]>("/api/v1/rewards/me/pending");
}

/**
 * Claim a reward.
 */
export async function claimReward(rewardId: number): Promise<ClaimRewardResponse> {
  return authFetch<ClaimRewardResponse>(`/api/v1/rewards/${rewardId}/claim`, {
    method: "POST",
  });
}

// ============================================================================
// Feed Curated Content API
// ============================================================================

import type { EventItem } from "@/api/events";
import type { NewsItem } from "@/api/news";

export interface CategoryStat {
  category: string;
  label: string;
  count: number;
}

export interface CuratedNewsResponse {
  items: NewsItem[];
  meta: {
    total_ranked?: number;
    cached_at?: string;
    message?: string;
    error?: string;
  };
}

export interface LocationStatsResponse {
  total: number;
  categories: CategoryStat[];
  formatted_text: string;
}

export interface CuratedEventsResponse {
  items: EventItem[];
  meta: {
    total_ranked?: number;
    cached_at?: string;
    message?: string;
    error?: string;
  };
}

/**
 * Fetch AI-curated news items (top 3 ranked by relevance to Turkish Dutch people).
 */
export async function fetchCuratedNews(): Promise<CuratedNewsResponse> {
  return apiFetch<CuratedNewsResponse>("/api/v1/feed/curated/news");
}

/**
 * Fetch location statistics with random category selection.
 */
export async function fetchLocationStats(): Promise<LocationStatsResponse> {
  return apiFetch<LocationStatsResponse>("/api/v1/feed/curated/locations");
}

/**
 * Fetch AI-curated events (top 3 ranked by relevance to Turkish diaspora).
 */
export async function fetchCuratedEvents(): Promise<CuratedEventsResponse> {
  return apiFetch<CuratedEventsResponse>("/api/v1/feed/curated/events");
}

// ============================================================================
// Authenticated Location Claims API
// ============================================================================

export interface AuthenticatedClaim {
  id: number;
  location_id: number;
  location_name: string | null;
  user_id: string;
  status: "pending" | "approved" | "rejected";
  google_business_link: string | null;
  logo_url: string | null;
  submitted_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimStatusResponse {
  claim: AuthenticatedClaim | null;
  is_claimed: boolean;
  can_claim: boolean;
}

export interface SubmitClaimRequest {
  google_business_link?: string;
}

/**
 * Submit a claim request for a location (authenticated users).
 */
export async function submitClaim(
  locationId: number,
  claim: SubmitClaimRequest
): Promise<AuthenticatedClaim> {
  return authFetch<AuthenticatedClaim>(`/api/v1/locations/${locationId}/claim`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(claim),
  });
}

/**
 * Get claim status for a specific location.
 */
export async function getClaimStatus(
  locationId: number
): Promise<ClaimStatusResponse> {
  return authFetch<ClaimStatusResponse>(
    `/api/v1/locations/${locationId}/claim-status`
  );
}

/**
 * List all claims for the authenticated user.
 */
export interface MyLocation {
  location_id: number;
  location_name: string | null;
  category: string | null;
  address: string | null;
  lat: number | null;
  lng: number | null;
  claimed_at: string | null;
  google_business_link: string | null;
  logo_url: string | null;
}

export async function getMyLocations(): Promise<MyLocation[]> {
  return authFetch<MyLocation[]>("/api/v1/locations/my-locations");
}

export async function getMyClaims(
  status?: "pending" | "approved" | "rejected"
): Promise<AuthenticatedClaim[]> {
  const params = status ? `?status=${status}` : "";
  return authFetch<AuthenticatedClaim[]>(`/api/v1/locations/my-claims${params}`);
}

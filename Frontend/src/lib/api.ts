// Frontend/src/lib/api.ts
import { supabase } from "@/lib/supabaseClient";
import { toast } from "sonner";

// API_BASE should be just the backend origin (no trailing slash, no /api/v1)
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

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
    throw new Error('Backend not configured (VITE_API_BASE_URL not set)');
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
        // Use timeout controller signal (will override init.signal if provided)
        // This ensures timeout always works even if caller provides their own signal
        const res = await fetch(url, {
          headers: {
            "Content-Type": "application/json",
            ...(init?.headers ?? {}),
          },
          ...init,
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
            try { await supabase.auth.signOut(); } catch { }
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

export async function whoAmI(): Promise<{ ok: boolean; admin_email: string }> {
  return authFetch("/api/v1/admin/whoami");
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

export interface CityProgressRotterdam {
  verifiedCount: number;
  candidateCount: number;
  coverageRatio: number;
  growthWeekly: number;
}

export interface CityProgress {
  rotterdam: CityProgressRotterdam;
}

export interface QualityMetrics {
  conversionRateVerified14d: number;
  taskErrorRate60m: number;
  google429Last60m: number;
}

export interface DiscoveryMetrics {
  newCandidatesPerWeek: number;
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

export async function getDiscoveryGrid(
  city?: string,
  district?: string
): Promise<DiscoveryGridCell[]> {
  const params = new URLSearchParams();
  if (city) params.set("city", city);
  if (district) params.set("district", district);
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

export interface LatencyMetrics {
  p50Ms: number;
  avgMs: number;
  maxMs: number;
}

export interface WeeklyCandidatesItem {
  weekStart: string;
  count: number;
}

export interface MetricsSnapshot {
  cityProgress: CityProgress;
  quality: QualityMetrics | null;
  discovery: DiscoveryMetrics | null;
  latency: LatencyMetrics | null;
  weeklyCandidates?: WeeklyCandidatesItem[] | null;
  workers: WorkerStatus[];
  currentRuns: WorkerRun[];
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

type RawCityProgressRotterdam = {
  verified_count: number;
  candidate_count: number;
  coverage_ratio: number;
  growth_weekly: number;
};

type RawMetricsSnapshot = {
  city_progress: {
    rotterdam: RawCityProgressRotterdam;
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

function normalizeCityProgress(rotterdam: RawCityProgressRotterdam): CityProgress {
  return {
    rotterdam: {
      verifiedCount: rotterdam.verified_count,
      candidateCount: rotterdam.candidate_count,
      coverageRatio: rotterdam.coverage_ratio,
      growthWeekly: rotterdam.growth_weekly,
    },
  };
}

function normalizeMetricsSnapshot(raw: RawMetricsSnapshot): MetricsSnapshot {
  return {
    cityProgress: normalizeCityProgress(raw.city_progress.rotterdam),
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
  };
}

export async function getMetricsSnapshot(): Promise<MetricsSnapshot> {
  const raw = await authFetch<RawMetricsSnapshot>("/api/v1/admin/metrics/snapshot");
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

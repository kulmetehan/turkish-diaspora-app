import { authFetch } from "@/lib/api";

export type AdminLocationListItem = {
    id: number;
    name: string;
    category?: string | null;
    state: string;
    confidence_score?: number | null;
    last_verified_at?: string | null;
    is_retired?: boolean | null;
};

export type AdminLocationDetail = AdminLocationListItem & {
    address?: string | null;
    notes?: string | null;
    business_status?: string | null;
    rating?: number | null;
    user_ratings_total?: number | null;
    is_probable_not_open_yet?: boolean | null;
};

export async function listAdminLocations(params: {
    search?: string;
    state?: string;
    category?: string;
    confidenceMin?: number;
    confidenceMax?: number;
    sort?: string;
    sortDirection?: "asc" | "desc";
    limit?: number;
    offset?: number;
}): Promise<{ rows: AdminLocationListItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params.search) q.set("search", params.search);
    if (params.state) q.set("state", params.state);
    if (params.category) q.set("category", params.category);
    if (params.sort && params.sort !== "NONE") q.set("sort", params.sort);
    if (params.sortDirection) q.set("sort_direction", params.sortDirection);
    if (params.confidenceMin != null) q.set("confidence_min", String(params.confidenceMin));
    if (params.confidenceMax != null) q.set("confidence_max", String(params.confidenceMax));
    q.set("limit", String(params.limit ?? 20));
    q.set("offset", String(params.offset ?? 0));
    // Always pass full API path (API_BASE is host-only)
    return authFetch(`/api/v1/admin/locations?${q.toString()}`);
}

export async function getAdminLocation(id: number): Promise<AdminLocationDetail> {
    return authFetch(`/api/v1/admin/locations/${id}`);
}

export type AdminLocationUpdateRequest = Partial<Pick<AdminLocationDetail,
    "name" | "address" | "category" | "state" | "notes" | "business_status" | "is_probable_not_open_yet" | "confidence_score"
>>;
export type AdminLocationUpdateOptions = AdminLocationUpdateRequest & { force?: boolean };

export async function updateAdminLocation(id: number, payload: AdminLocationUpdateOptions): Promise<AdminLocationDetail> {
    return authFetch(`/api/v1/admin/locations/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function retireAdminLocation(id: number): Promise<{ ok: boolean }> {
    return authFetch(`/api/v1/admin/locations/${id}`, {
        method: "DELETE",
    });
}

export type AdminLocationCreateRequest = {
    name: string;
    address: string;
    lat: number;
    lng: number;
    category: string;
    notes?: string;
    evidence_urls?: string[];
};

export async function createAdminLocation(payload: AdminLocationCreateRequest): Promise<AdminLocationDetail> {
    return authFetch(`/api/v1/admin/locations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export type BulkAction =
    | { type: "verify"; force?: boolean; clear_retired?: boolean }
    | { type: "retire" }
    | { type: "adjust_confidence"; value: number };

export async function bulkUpdateLocations(payload: { ids: number[]; action: BulkAction }): Promise<{
    ok: boolean;
    updated: number[];
    errors: { id: number; detail: string }[];
}> {
    return authFetch(`/api/v1/admin/locations/bulk-update`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function seedDevLocation(): Promise<{ ok: boolean; id?: number }> {
    return authFetch(`/api/v1/admin/locations/dev-seed`, { method: "POST" });
}

type LocationStateOption = { value: string; label: string };
type LocationStatesResponse = { states: LocationStateOption[] };

export async function listLocationStates(): Promise<LocationStatesResponse> {
    const primary = "/api/v1/admin/location-states";
    const legacy = "/api/v1/admin/locations/location-states";

    const tryFetch = (path: string) => authFetch<LocationStatesResponse>(path);

    try {
        return await tryFetch(primary);
    } catch (err: any) {
        const message = typeof err?.message === "string" ? err.message : "";
        if (/API 40(4|5)/.test(message)) {
            return await tryFetch(legacy);
        }
        throw err;
    }
}

// --- Location State Metrics ---

export type LocationStateBucket = {
    state: string;
    count: number;
};

export type LocationStateMetrics = {
    total: number;
    by_state: LocationStateBucket[];
};

export async function getLocationStateMetrics(): Promise<LocationStateMetrics> {
    return authFetch<LocationStateMetrics>("/api/v1/admin/metrics/location_states");
}

export type NewsPerDayDTO = {
    date: string;
    count: number;
};

export type NewsLabelCountDTO = {
    label: string;
    count: number;
};

export type NewsErrorsDTO = {
    ingest_errors_last_24h: number;
    classify_errors_last_24h: number;
    pending_items_last_24h: number;
};

export type NewsMetricsSnapshotDTO = {
    items_per_day_last_7d: NewsPerDayDTO[];
    items_by_source_last_24h: NewsLabelCountDTO[];
    items_by_feed_last_24h: NewsLabelCountDTO[];
    errors: NewsErrorsDTO;
};

export async function getNewsMetricsAdmin(): Promise<NewsMetricsSnapshotDTO> {
    return authFetch<NewsMetricsSnapshotDTO>("/api/v1/admin/metrics/news");
}

export type EventPerDayDTO = {
    date: string;
    count: number;
};

export type EventSourceStatDTO = {
    source_id: number;
    source_key: string;
    source_name: string;
    last_success_at?: string | null;
    last_error_at?: string | null;
    last_error?: string | null;
    events_last_24h: number;
    total_events: number;
};

export type EventEnrichmentMetricsDTO = {
    total: number;
    enriched: number;
    pending: number;
    errors: number;
    avg_confidence_score?: number | null;
    category_breakdown: Array<{ category_key: string; count: number }>;
};

export type EventDedupeMetricsDTO = {
    canonical_events: number;
    duplicate_events: number;
    duplicates_last_7d: number;
    canonical_ratio?: number | null;
};

export type EventMetricsSnapshotDTO = {
    events_per_day_last_7d: EventPerDayDTO[];
    sources: EventSourceStatDTO[];
    total_events_last_30d: number;
    enrichment?: EventEnrichmentMetricsDTO;
    dedupe?: EventDedupeMetricsDTO;
};

export async function getEventMetricsAdmin(): Promise<EventMetricsSnapshotDTO> {
    return authFetch<EventMetricsSnapshotDTO>("/api/v1/admin/metrics/events");
}

export type AdminEventCandidate = {
    id: number;
    event_source_id: number;
    source_key: string;
    source_name?: string | null;
    title: string;
    description?: string | null;
    location_text?: string | null;
    url?: string | null;
    start_time_utc: string;
    end_time_utc?: string | null;
    duplicate_of_id?: number | null;
    duplicate_score?: number | null;
    has_duplicates?: boolean;
    state: "candidate" | "verified" | "published" | "rejected";
    created_at: string;
    updated_at: string;
};

export type AdminEventCandidateListResponse = {
    items: AdminEventCandidate[];
    total: number;
    limit: number;
    offset: number;
};

export type AdminEventDuplicateCluster = {
    canonical: AdminEventCandidate;
    duplicates: AdminEventCandidate[];
};

export async function listEventCandidatesAdmin(params?: {
    state?: "candidate" | "verified" | "published" | "rejected";
    sourceId?: number;
    sourceKey?: string;
    search?: string;
    duplicatesOnly?: boolean;
    canonicalOnly?: boolean;
    limit?: number;
    offset?: number;
}): Promise<AdminEventCandidateListResponse> {
    const q = new URLSearchParams();
    if (params?.state) q.set("state", params.state);
    if (params?.sourceId) q.set("source_id", String(params.sourceId));
    if (params?.sourceKey) q.set("source_key", params.sourceKey.toLowerCase());
    if (params?.search) q.set("search", params.search);
    if (params?.duplicatesOnly) q.set("duplicates_only", "true");
    if (params?.canonicalOnly) q.set("canonical_only", "true");
    q.set("limit", String(params?.limit ?? 50));
    q.set("offset", String(params?.offset ?? 0));
    const query = q.toString();
    return authFetch<AdminEventCandidateListResponse>(
        `/api/v1/admin/events/candidates?${query}`,
    );
}

export async function getEventCandidateDuplicatesAdmin(
    id: number,
): Promise<AdminEventDuplicateCluster> {
    return authFetch<AdminEventDuplicateCluster>(
        `/api/v1/admin/events/candidates/${id}/duplicates`,
    );
}

export async function verifyEventCandidateAdmin(id: number): Promise<AdminEventCandidate> {
    return authFetch<AdminEventCandidate>(
        `/api/v1/admin/events/candidates/${id}/verify`,
        { method: "POST" },
    );
}

export async function publishEventCandidateAdmin(id: number): Promise<AdminEventCandidate> {
    return authFetch<AdminEventCandidate>(
        `/api/v1/admin/events/candidates/${id}/publish`,
        { method: "POST" },
    );
}

export async function rejectEventCandidateAdmin(id: number): Promise<AdminEventCandidate> {
    return authFetch<AdminEventCandidate>(
        `/api/v1/admin/events/candidates/${id}/reject`,
        { method: "POST" },
    );
}

// Import CategoryOption type from fetchLocations
import type { CategoryOption } from "@/api/fetchLocations";

type LocationCategoriesResponse = { categories: Array<{ key: string; label: string }> };

export async function listAdminLocationCategories(): Promise<CategoryOption[]> {
    try {
        const res = await authFetch<LocationCategoriesResponse>("/api/v1/admin/location-categories");
        if (Array.isArray(res?.categories)) {
            return res.categories.map((cat) => ({
                key: cat.key.toLowerCase().trim(),
                label: cat.label || cat.key,
            })).filter((cat) => cat.key && cat.key !== "other");
        }
        return [];
    } catch (err: any) {
        if (import.meta.env.DEV) {
            // eslint-disable-next-line no-console
            console.warn("Failed to fetch location categories", err);
        }
        return [];
    }
}

export interface RunWorkerResponse {
    run_id: string | null;
    bot: string;
    city?: string | null;
    category?: string | null;
    tracking_available?: boolean;
    detail?: string;
}

export async function runWorker(params: { bot: string; city?: string; category?: string; max_jobs?: number }): Promise<RunWorkerResponse> {
    return authFetch<RunWorkerResponse>("/api/v1/admin/workers/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });
}

// --- Discovery Jobs Enqueuing ---

export interface EnqueueJobsRequest {
    city_key: string;
    categories?: string[];
    districts?: string[];
}

export interface EnqueueJobsResponse {
    jobs_created: number;
    job_ids: string[];
    preview: {
        city: string;
        districts: string[];
        categories: string[];
        estimated_jobs: number;
    };
}

export async function enqueueDiscoveryJobs(
    params: EnqueueJobsRequest
): Promise<EnqueueJobsResponse> {
    return authFetch<EnqueueJobsResponse>("/api/v1/admin/discovery/enqueue_jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });
}

export interface CityInfo {
    name: string;
    key: string;
    has_districts: boolean;
}

export interface CitiesResponse {
    cities: CityInfo[];
}

export async function getCities(): Promise<CityInfo[]> {
    const response = await authFetch<CitiesResponse>("/api/v1/admin/discovery/cities");
    return response.cities;
}

// Note: getCityDistricts() is already defined in ../lib/api.ts - import from there if needed

// --- Worker Runs ---

export interface WorkerRunListItem {
    id: string;
    bot: string;
    city?: string | null;
    category?: string | null;
    status: string;
    progress: number;
    started_at?: string | null;
    finished_at?: string | null;
    duration_seconds?: number | null;
}

export interface WorkerRunListResponse {
    items: WorkerRunListItem[];
    total: number;
    limit: number;
    offset: number;
}

export interface WorkerRunDetail {
    id: string;
    bot: string;
    city?: string | null;
    category?: string | null;
    status: string;
    progress: number;
    counters?: Record<string, unknown> | null;
    error_message?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
    created_at: string;
    duration_seconds?: number | null;
    parameters?: Record<string, unknown> | null;
}

export async function listWorkerRuns(params?: {
    bot?: string;
    status?: string;
    since?: string;
    limit?: number;
    offset?: number;
}): Promise<WorkerRunListResponse> {
    const q = new URLSearchParams();
    if (params?.bot) q.set("bot", params.bot);
    if (params?.status) q.set("status", params.status);
    if (params?.since) q.set("since", params.since);
    q.set("limit", String(params?.limit ?? 20));
    q.set("offset", String(params?.offset ?? 0));
    return authFetch<WorkerRunListResponse>(`/api/v1/admin/workers/runs?${q.toString()}`);
}

export async function getWorkerRunDetail(runId: string): Promise<WorkerRunDetail> {
    return authFetch<WorkerRunDetail>(`/api/v1/admin/workers/runs/${runId}`);
}

// --- AI Logs ---

export type AILogItem = {
    id: number;
    location_id?: number | null;
    news_id?: number | null;
    action_type: string;
    model_used?: string | null;
    confidence_score?: number | null;
    category?: string | null;
    created_at: string;
    validated_output?: Record<string, unknown> | null;
    is_success: boolean;
    error_message?: string | null;
    explanation: string;
    news_source_key?: string | null;
    news_source_name?: string | null;
};

export type AILogsResponse = {
    items: AILogItem[];
    total: number;
    limit: number;
    offset: number;
};

export type AILogDetail = {
    id: number;
    location_id?: number | null;
    news_id?: number | null;
    action_type: string;
    model_used?: string | null;
    prompt?: Record<string, unknown> | string | null;
    raw_response?: Record<string, unknown> | string | null;
    validated_output?: Record<string, unknown> | string | null;
    is_success: boolean;
    error_message?: string | null;
    created_at: string;
    news_source_key?: string | null;
    news_source_name?: string | null;
    news_title?: string | null;
};

export async function listAILogs(params?: {
    location_id?: number;
    action_type?: string;
    since?: string;
    limit?: number;
    offset?: number;
    news_only?: boolean;
    news_id?: number;
    source_key?: string;
    source_name?: string;
}): Promise<AILogsResponse> {
    const q = new URLSearchParams();
    if (params?.location_id != null) q.set("location_id", String(params.location_id));
    if (params?.action_type) q.set("action_type", params.action_type);
    if (params?.since) q.set("since", params.since);
    if (params?.news_only !== undefined) q.set("news_only", String(params.news_only));
    if (params?.news_id != null) q.set("news_id", String(params.news_id));
    if (params?.source_key) q.set("source_key", params.source_key);
    if (params?.source_name) q.set("source_name", params.source_name);
    q.set("limit", String(params?.limit ?? 20));
    q.set("offset", String(params?.offset ?? 0));
    return authFetch<AILogsResponse>(`/api/v1/admin/ai/logs?${q.toString()}`);
}

export async function getAILogDetail(id: number): Promise<AILogDetail> {
    return authFetch<AILogDetail>(`/api/v1/admin/ai/logs/${id}`);
}

// --- Tasks ---

export type TaskItem = {
    id: number;
    task_type: string;
    status: string;
    created_at: string;
    last_attempted_at?: string | null;
    location_id?: number | null;
    attempts: number;
    payload?: Record<string, unknown> | null;
};

export type TaskSummary = {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
};

export type TasksResponse = {
    summary: Record<string, TaskSummary>;
    items: TaskItem[];
    total: number;
    limit: number;
    offset: number;
};

export async function getTasks(params?: {
    task_type?: string;
    status?: string;
    since?: string;
    limit?: number;
    offset?: number;
}): Promise<TasksResponse> {
    const q = new URLSearchParams();
    if (params?.task_type) q.set("task_type", params.task_type);
    if (params?.status) q.set("status", params.status);
    if (params?.since) q.set("since", params.since);
    q.set("limit", String(params?.limit ?? 50));
    q.set("offset", String(params?.offset ?? 0));
    return authFetch<TasksResponse>(`/api/v1/admin/tasks?${q.toString()}`);
}


// --- Event Sources ---

export type EventSourceDTO = {
    id: number;
    key: string;
    name: string;
    base_url: string;
    list_url?: string | null;
    selectors: Record<string, unknown>;
    interval_minutes: number;
    status: "active" | "disabled";
    last_run_at?: string | null;
    last_success_at?: string | null;
    last_error_at?: string | null;
    last_error?: string | null;
    created_at: string;
    updated_at: string;
};

export type EventSourcePayload = {
    key: string;
    name: string;
    base_url: string;
    list_url?: string | null;
    selectors: Record<string, unknown>;
    interval_minutes: number;
    status?: "active" | "disabled";
};

type EventSourceUpdatePayload = Partial<EventSourcePayload>;

type EventSourcesResponse = {
    items: EventSourceDTO[];
};

export async function listEventSourcesAdmin(status?: "active" | "disabled"): Promise<EventSourceDTO[]> {
    const q = new URLSearchParams();
    if (status) {
        q.set("status", status);
    }
    const query = q.toString();
    const path = query ? `/api/v1/admin/event-sources?${query}` : "/api/v1/admin/event-sources";
    const response = await authFetch<EventSourcesResponse>(path);
    return Array.isArray(response.items) ? response.items : [];
}

export async function createEventSourceAdmin(payload: EventSourcePayload): Promise<EventSourceDTO> {
    return authFetch<EventSourceDTO>("/api/v1/admin/event-sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function updateEventSourceAdmin(id: number, payload: EventSourceUpdatePayload): Promise<EventSourceDTO> {
    return authFetch<EventSourceDTO>(`/api/v1/admin/event-sources/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function toggleEventSourceStatusAdmin(id: number): Promise<{ id: number; status: "active" | "disabled" }> {
    return authFetch<{ id: number; status: "active" | "disabled" }>(`/api/v1/admin/event-sources/${id}/toggle-status`, {
        method: "POST",
    });
}



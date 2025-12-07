import { authFetch, API_BASE, getAdminKey } from "@/lib/api";
import { supabase } from "@/lib/supabaseClient";

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

export type AdminLocationBulkImportError = {
    row_number: number;
    message: string;
};

export type AdminLocationBulkImportResult = {
    rows_total: number;
    rows_processed: number;
    rows_created: number;
    rows_failed: number;
    errors: AdminLocationBulkImportError[];
};

export async function bulkImportLocations(file: File): Promise<AdminLocationBulkImportResult> {
    const formData = new FormData();
    formData.append("file", file);

    // Get Supabase JWT token (same as authFetch does)
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
        throw new Error("Not authenticated");
    }

    const url = `${API_BASE}/api/v1/admin/locations/bulk_import`;
    
    const response = await fetch(url, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`,
            // Do NOT set Content-Type - browser will set it with boundary for multipart/form-data
        },
        body: formData,
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Bulk import failed");
    }

    return response.json();
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

// --- City Management Types ---

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

export interface DistrictCreate {
    name: string;
    center_lat: number;
    center_lng: number;
}

export interface DistrictUpdate {
    name?: string;
    center_lat?: number;
    center_lng?: number;
}

export interface CityCreate {
    city_name: string;
    country?: string;
    center_lat: number;
    center_lng: number;
    districts?: DistrictCreate[];
}

export interface CityUpdate {
    city_name?: string;
    country?: string;
    center_lat?: number;
    center_lng?: number;
}

export interface DistrictDetail {
    key: string;
    name: string;
    center_lat: number;
    center_lng: number;
    bbox: {
        lat_min: number;
        lat_max: number;
        lng_min: number;
        lng_max: number;
    };
}

export interface CityDetailResponse {
    city_key: string;
    city_name: string;
    country: string;
    center_lat: number;
    center_lng: number;
    districts: DistrictDetail[];
}

// --- City Management API Functions ---

export async function getCitiesOverview(): Promise<CitiesOverview> {
    return authFetch<CitiesOverview>("/api/v1/admin/cities");
}

export async function getCityDetail(cityKey: string): Promise<CityDetailResponse> {
    return authFetch<CityDetailResponse>(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}`);
}

export async function createCity(city: CityCreate): Promise<CityReadiness> {
    return authFetch<CityReadiness>("/api/v1/admin/cities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(city),
    });
}

export async function updateCity(cityKey: string, city: CityUpdate): Promise<CityReadiness> {
    return authFetch<CityReadiness>(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(city),
    });
}

export async function deleteCity(cityKey: string): Promise<void> {
    await authFetch(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}`, {
        method: "DELETE",
    });
}

export async function createDistrict(cityKey: string, district: DistrictCreate): Promise<{ ok: boolean; city_key: string; district_key: string; bbox: { lat_min: number; lat_max: number; lng_min: number; lng_max: number } }> {
    return authFetch(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}/districts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(district),
    });
}

export async function updateDistrict(
    cityKey: string,
    districtKey: string,
    district: DistrictUpdate
): Promise<{ ok: boolean; city_key: string; district_key: string; bbox: { lat_min: number; lat_max: number; lng_min: number; lng_max: number } }> {
    return authFetch(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}/districts/${encodeURIComponent(districtKey)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(district),
    });
}

export async function deleteDistrict(cityKey: string, districtKey: string): Promise<void> {
    await authFetch(`/api/v1/admin/cities/${encodeURIComponent(cityKey)}/districts/${encodeURIComponent(districtKey)}`, {
        method: "DELETE",
    });
}

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

// ============================================================================
// Admin Polls API
// ============================================================================

export type AdminPollOption = {
    id: number;
    option_text: string;
    display_order: number;
};

export type AdminPoll = {
    id: number;
    title: string;
    question: string;
    poll_type: "single_choice" | "multi_choice";
    options: AdminPollOption[];
    is_sponsored: boolean;
    starts_at: string | null;
    ends_at: string | null;
    targeting_city_key: string | null;
    created_at: string;
};

export type AdminPollCreateRequest = {
    title: string;
    question: string;
    poll_type: "single_choice" | "multi_choice";
    options: Array<{ option_text: string; display_order: number }>;
    is_sponsored?: boolean;
    starts_at?: string | null;
    ends_at?: string | null;
    targeting_city_key?: string | null;
};

export type AdminPollUpdateRequest = {
    title?: string;
    question?: string;
    poll_type?: "single_choice" | "multi_choice";
    is_sponsored?: boolean;
    starts_at?: string | null;
    ends_at?: string | null;
    targeting_city_key?: string | null;
};

export async function listAdminPolls(params?: {
    limit?: number;
    offset?: number;
}): Promise<AdminPoll[]> {
    const q = new URLSearchParams();
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return authFetch<AdminPoll[]>(`/api/v1/admin/polls?${q.toString()}`);
}

export async function createAdminPoll(payload: AdminPollCreateRequest): Promise<AdminPoll> {
    return authFetch<AdminPoll>("/api/v1/admin/polls", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function updateAdminPoll(id: number, payload: AdminPollUpdateRequest): Promise<AdminPoll> {
    return authFetch<AdminPoll>(`/api/v1/admin/polls/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function deleteAdminPoll(id: number): Promise<{ ok: boolean; poll_id: number }> {
    return authFetch<{ ok: boolean; poll_id: number }>(`/api/v1/admin/polls/${id}`, {
        method: "DELETE",
    });
}

// ============================================================================
// Admin Reports API
// ============================================================================

export type AdminReport = {
    id: number;
    report_type: "location" | "note" | "reaction" | "user";
    target_id: number;
    reason: string;
    details: string | null;
    status: "pending" | "resolved" | "dismissed";
    created_at: string;
};

export type AdminReportUpdateRequest = {
    status: "pending" | "resolved" | "dismissed";
    resolution_notes?: string | null;
};

export async function listAdminReports(params?: {
    status?: "pending" | "resolved" | "dismissed";
    report_type?: "location" | "note" | "reaction" | "user";
    limit?: number;
    offset?: number;
}): Promise<AdminReport[]> {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.report_type) q.set("report_type", params.report_type);
    q.set("limit", String(params?.limit ?? 100));
    q.set("offset", String(params?.offset ?? 0));
    return authFetch<AdminReport[]>(`/api/v1/reports/admin?${q.toString()}`);
}

export async function updateAdminReport(
    id: number,
    payload: AdminReportUpdateRequest
): Promise<AdminReport> {
    return authFetch<AdminReport>(`/api/v1/reports/admin/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function removeReportedContent(reportId: number): Promise<{
    ok: boolean;
    removed: boolean;
    report: AdminReport;
}> {
    return authFetch<{ ok: boolean; removed: boolean; report: AdminReport }>(
        `/api/v1/reports/admin/${reportId}/remove-content`,
        {
            method: "POST",
        }
    );
}

// ============================================================================
// Admin Bulletin API
// ============================================================================

export type AdminBulletinPost = {
    id: number;
    title: string;
    description?: string;
    category: string;
    city?: string;
    moderation_status: string;
    moderation_result?: {
        decision: string;
        reason: string;
        details?: string;
    };
    created_at: string;
    creator_type: string;
    view_count: number;
    contact_count: number;
};

export async function getBulletinReviewQueue(status?: string): Promise<AdminBulletinPost[]> {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    return authFetch<AdminBulletinPost[]>(`/api/v1/admin/bulletin/review-queue?${params.toString()}`);
}

export async function moderateBulletinPost(
    postId: number,
    action: "approve" | "reject",
    reason?: string
): Promise<{ ok: boolean; message: string }> {
    return authFetch<{ ok: boolean; message: string }>(`/api/v1/admin/bulletin/posts/${postId}/moderate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, reason }),
    });
}


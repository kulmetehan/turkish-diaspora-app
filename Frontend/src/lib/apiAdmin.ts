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



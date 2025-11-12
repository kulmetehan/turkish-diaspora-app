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
    limit?: number;
    offset?: number;
}): Promise<{ rows: AdminLocationListItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params.search) q.set("search", params.search);
    if (params.state) q.set("state", params.state);
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



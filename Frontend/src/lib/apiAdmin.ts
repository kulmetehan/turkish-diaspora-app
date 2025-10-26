import { authFetch } from "@/lib/api";

export type AdminLocationListItem = {
    id: number;
    name: string;
    category?: string | null;
    state: string;
    confidence_score?: number | null;
    last_verified_at?: string | null;
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
    // Explicit API prefix to align with backend router
    return authFetch(`/api/v1/admin/locations?${q.toString()}`);
}

export async function getAdminLocation(id: number): Promise<AdminLocationDetail> {
    return authFetch(`/api/v1/admin/locations/${id}`);
}

export type AdminLocationUpdateRequest = Partial<Pick<AdminLocationDetail,
    "name" | "address" | "category" | "state" | "notes" | "business_status" | "is_probable_not_open_yet"
>>;

export async function updateAdminLocation(id: number, payload: AdminLocationUpdateRequest): Promise<AdminLocationDetail> {
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



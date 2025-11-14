export interface AdminLocationFilters {
    search: string;
    stateFilter: string;
    categoryFilter: string;
    confidenceMin: string;
    confidenceMax: string;
    sort: "NONE" | "latest_added" | "latest_verified";
    sortDirection: "asc" | "desc";
    limit: number;
    offset: number;
}

const STORAGE_KEY = "tda_admin_locations_filters_v1";

export function loadAdminLocationFilters(): Partial<AdminLocationFilters> {
    if (typeof window === "undefined") {
        return {};
    }

    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) {
            return {};
        }

        const parsed = JSON.parse(stored) as Partial<AdminLocationFilters>;
        
        // Validate and sanitize values
        const result: Partial<AdminLocationFilters> = {};
        
        if (typeof parsed.search === "string") {
            result.search = parsed.search;
        }
        if (typeof parsed.stateFilter === "string") {
            result.stateFilter = parsed.stateFilter;
        }
        if (typeof parsed.categoryFilter === "string") {
            result.categoryFilter = parsed.categoryFilter;
        }
        if (typeof parsed.confidenceMin === "string") {
            result.confidenceMin = parsed.confidenceMin;
        }
        if (typeof parsed.confidenceMax === "string") {
            result.confidenceMax = parsed.confidenceMax;
        }
        if (parsed.sort === "NONE" || parsed.sort === "latest_added" || parsed.sort === "latest_verified") {
            result.sort = parsed.sort;
        }
        if (parsed.sortDirection === "asc" || parsed.sortDirection === "desc") {
            result.sortDirection = parsed.sortDirection;
        }
        if (typeof parsed.limit === "number" && parsed.limit >= 1 && parsed.limit <= 200) {
            result.limit = parsed.limit;
        }
        if (typeof parsed.offset === "number" && parsed.offset >= 0) {
            result.offset = parsed.offset;
        }

        return result;
    } catch (error) {
        // JSON parse error or other error - return empty object
        if (import.meta.env.DEV) {
            // eslint-disable-next-line no-console
            console.warn("Failed to load admin location filters from localStorage:", error);
        }
        return {};
    }
}

export function saveAdminLocationFilters(filters: Partial<AdminLocationFilters>): void {
    if (typeof window === "undefined") {
        return;
    }

    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch (error) {
        // localStorage quota exceeded or other error - fail silently
        if (import.meta.env.DEV) {
            // eslint-disable-next-line no-console
            console.warn("Failed to save admin location filters to localStorage:", error);
        }
    }
}


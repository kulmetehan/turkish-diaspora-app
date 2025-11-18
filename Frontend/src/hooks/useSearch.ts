// Frontend/src/hooks/useSearch.ts
// NOTE: 'dataset' is the new preferred input (e.g. globalLocations).
// 'locations' is kept for backward compatibility and will be removed later.
import type { LocationMarker } from "@/api/fetchLocations";
import { useEffect, useMemo, useRef, useState } from "react";

type UseSearchParams = {
    dataset?: LocationMarker[];   // NEW: preferred source (e.g. globalLocations)
    locations?: LocationMarker[]; // LEGACY: backward compatibility, will be removed later
    search: string;
    category: string; // "all" or canonical key
    debounceMs?: number; // default 350
    cacheSize?: number;  // default 30
};

type UseSearchResult = {
    debouncedQuery: string;
    filtered: LocationMarker[];
    suggestions: string[];
};

function normalizeCategory(input: string | undefined | null): string {
    return String(input ?? "").toLowerCase();
}

/**
 * Simple in-memory LRU cache keyed by query|category → array of ids.
 */
function useLruCache(maxSize: number) {
    const mapRef = useRef<Map<string, string[]>>(new Map());

    const get = (key: string): string[] | undefined => {
        const map = mapRef.current;
        const value = map.get(key);
        if (value) {
            // refresh LRU order
            map.delete(key);
            map.set(key, value);
        }
        return value;
    };

    const set = (key: string, value: string[]) => {
        const map = mapRef.current;
        if (map.has(key)) map.delete(key);
        map.set(key, value);
        if (map.size > maxSize) {
            const oldestKey = map.keys().next().value as string | undefined;
            if (oldestKey) map.delete(oldestKey);
        }
    };

    const clear = () => {
        mapRef.current.clear();
    };

    return { get, set, clear };
}

export function useSearch(params: UseSearchParams): UseSearchResult {
    const { dataset, locations, search, category, debounceMs = 350, cacheSize = 30 } = params;

    // Use dataset as preferred source, fallback to locations for backward compatibility
    const source = dataset ?? locations ?? [];

    // Debounced query
    const [debouncedQuery, setDebouncedQuery] = useState("");
    useEffect(() => {
        const handle = window.setTimeout(() => setDebouncedQuery(search), debounceMs);
        return () => window.clearTimeout(handle);
    }, [search, debounceMs]);

    // LRU cache for filtered ids
    const lru = useLruCache(cacheSize);

    const filteredIds = useMemo(() => {
        const q = debouncedQuery.trim().toLowerCase();
        const cat = normalizeCategory(category);
        const key = `${q}|${cat}`;

        const cached = lru.get(key);
        if (cached) return cached;

        const ids: string[] = [];
        for (const l of source) {
            const locCat = normalizeCategory((l as any).category_key ?? l.category);
            if (cat !== "all" && locCat !== cat) continue;
            if (q && !String(l.name ?? "").toLowerCase().includes(q)) continue;
            ids.push(String(l.id));
        }
        lru.set(key, ids);
        return ids;
    }, [source, debouncedQuery, category]);

    const filtered = useMemo(() => {
        if (!filteredIds.length) return [] as LocationMarker[];
        // Build a quick id → location map for stable ordering by original list
        const byId = new Map<string, LocationMarker>();
        for (const l of source) byId.set(String(l.id), l);
        return filteredIds
            .map((id) => byId.get(id))
            .filter((l): l is LocationMarker => Boolean(l));
    }, [filteredIds, source]);

    // Local suggestions derived from source (name + category keywords)
    const suggestions = useMemo(() => {
        const q = debouncedQuery.trim().toLowerCase();
        if (!q) return [];

        const seen = new Set<string>();
        const out: string[] = [];

        // Name suggestions
        for (const l of source) {
            const name = String(l.name ?? "");
            if (!name) continue;
            if (name.toLowerCase().includes(q)) {
                const s = name;
                if (!seen.has(s)) {
                    seen.add(s);
                    out.push(s);
                    if (out.length >= 8) break;
                }
            }
        }

        // If still room, add category label/key suggestions
        if (out.length < 8) {
            for (const l of source) {
                const key = normalizeCategory((l as any).category_key ?? l.category);
                const label = String((l as any).category_label ?? l.category ?? "");
                const candidates = [label, key].filter(Boolean) as string[];
                for (const c of candidates) {
                    const s = c.trim();
                    if (!s) continue;
                    if (s.toLowerCase().includes(q) && !seen.has(s)) {
                        seen.add(s);
                        out.push(s);
                        if (out.length >= 8) break;
                    }
                }
                if (out.length >= 8) break;
            }
        }

        return out;
    }, [debouncedQuery, source]);

    // Clear cache when base dataset changes notably (e.g., upon reload)
    useEffect(() => {
        // Heuristic: reset cache when number of locations changes
        // (keeps it simple and safe for this session-only cache)
        lru.clear();
    }, [source.length]);

    return { debouncedQuery, filtered, suggestions };
}

export default useSearch;



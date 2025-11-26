import { useCallback, useEffect, useState } from "react";

import { listEventSourcesAdmin, type EventSourceDTO } from "@/lib/apiAdmin";

export function useAdminEventSources(status?: "active" | "disabled") {
    const [sources, setSources] = useState<EventSourceDTO[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const fetchSources = useCallback(
        async (overrideStatus?: "active" | "disabled") => {
            setLoading(true);
            try {
                const data = await listEventSourcesAdmin(overrideStatus ?? status);
                setSources(data);
                setError(null);
            } catch (err: any) {
                setError(err?.message || "Failed to load event sources");
            } finally {
                setLoading(false);
            }
        },
        [status]
    );

    useEffect(() => {
        void fetchSources(status);
    }, [status, fetchSources]);

    return {
        sources,
        loading,
        error,
        refresh: fetchSources,
        setSources,
    };
}





import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type VisibleCitySample = { city?: string | null };

export interface ViewportState {
    zoom: number | null;
    centerLat: number | null;
    centerLng: number | null;
    selectedCity: string | null;
    visible: VisibleCitySample[] | null;
}

export interface ViewportContextValue {
    viewport: ViewportState;
    setViewport: (partial: Partial<ViewportState>) => void;
    setSelectedCity: (city: string | null) => void;
}

const DEFAULT_STATE: ViewportState = {
    zoom: null,
    centerLat: null,
    centerLng: null,
    selectedCity: null,
    visible: null,
};

const ViewportContext = createContext<ViewportContextValue | null>(null);

export function ViewportProvider({ children }: { children: ReactNode }) {
    const [viewport, setViewportState] = useState<ViewportState>(DEFAULT_STATE);

    const setViewport = useCallback((partial: Partial<ViewportState>) => {
        setViewportState((prev) => ({
            ...prev,
            ...partial,
        }));
    }, []);

    const setSelectedCity = useCallback((city: string | null) => {
        setViewportState((prev) => ({
            ...prev,
            selectedCity: city,
        }));
    }, []);

    const value = useMemo<ViewportContextValue>(
        () => ({
            viewport,
            setViewport,
            setSelectedCity,
        }),
        [viewport, setViewport, setSelectedCity],
    );

    return <ViewportContext.Provider value={value}>{children}</ViewportContext.Provider>;
}

export function useViewportContext(): ViewportContextValue {
    const ctx = useContext(ViewportContext);
    if (!ctx) {
        throw new Error("useViewportContext must be used within a ViewportProvider");
    }
    return ctx;
}


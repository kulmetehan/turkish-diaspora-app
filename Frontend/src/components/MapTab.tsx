// Frontend/src/components/MapTab.tsx
// Map tab content extracted from App.tsx for persistent layer architecture

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import Filters from "@/components/Filters";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import UnifiedLocationDetail from "@/components/UnifiedLocationDetail";
import { AppHeader } from "@/components/feed/AppHeader";
import { AppViewportShell } from "@/components/layout";
import NoteDialog from "@/components/location/NoteDialog";
import { MapListToggle } from "@/components/map/MapListToggle";
import { CategoryChips } from "@/components/search/CategoryChips";
import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import { ViewportProvider } from "@/contexts/viewport";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";
import { clearFocusId, onHashChange, readFocusId, readViewMode, writeFocusId, writeViewMode, type ViewMode } from "@/lib/routing/viewMode";
import { navigationActions, useMapNavigation } from "@/state/navigation";

import { fetchCategories, fetchLocations, fetchLocationsCount, type CategoryOption, type LocationMarker } from "@/api/fetchLocations";
import { createNote, updateNote, type NoteResponse } from "@/lib/api";
import { toast } from "sonner";

export default function MapTab() {
    // Global locations state (viewport-independent, fetched on mount)
    const [globalLocations, setGlobalLocations] = useState<LocationMarker[]>([]);
    const [globalLocationsLoading, setGlobalLocationsLoading] = useState(true);
    const [globalLocationsError, setGlobalLocationsError] = useState<string | null>(null);

    // Viewport locations state (for map marker rendering performance)
    const [viewportLocations, setViewportLocations] = useState<LocationMarker[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewportBbox, setViewportBbox] = useState<string | null>(null);
    const debounceTimeoutRef = useRef<number | null>(null);

    // Global categories state (viewport-independent)
    const [globalCategories, setGlobalCategories] = useState<CategoryOption[]>([]);
    const [categoriesLoading, setCategoriesLoading] = useState<boolean>(true);
    const [categoriesError, setCategoriesError] = useState<string | null>(null);

    // Navigation state (Map tab)
    const mapNavigation = useMapNavigation();

    // Use navigation store for filters and selection
    const filters = mapNavigation.filters;
    const highlightedId = mapNavigation.selectedLocationId;

    // For detailId, we can store it separately since it's a UI state (overlay open/closed)
    const [detailIdLocal, setDetailIdLocal] = useState<string | null>(null);

    // Note dialog state
    const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
    const [editingNote, setEditingNote] = useState<NoteResponse | null>(null);

    // Effective detailId: use local state if set, otherwise null
    const effectiveDetailId = detailIdLocal;

    // Bottom sheet state
    // Responsive breakpoint detection
    const isDesktop = useMediaQuery("(min-width: 1024px)");
    const isCompact = useMediaQuery("(max-width: 767px)");

    const [viewMode, setViewMode] = useState<ViewMode>(() => {
        if (typeof window === "undefined") return "map";
        return readViewMode();
    });
    const [pendingFocusId, setPendingFocusId] = useState<string | null>(() => {
        if (typeof window === "undefined") return null;
        return readFocusId();
    });
    const inFlightRequestRef = useRef<{ bbox: string | null; controller: AbortController } | null>(null);
    const suppressNextViewportFetchRef = useRef(false);
    const lastSettledBboxRef = useRef<string | null>(null);
    const hasSettledRef = useRef(false);
    const mapHeadingRef = useRef<HTMLHeadingElement | null>(null);
    const hasAppliedInitialFocusRef = useRef(false);
    const listScrollContainerRef = useRef<HTMLDivElement | null>(null);
    const scrollRestoredRef = useRef(false);
    const scrollThrottleRef = useRef<number | null>(null);
    const mapHeadingId = useId();

    useEffect(() => {
        if (typeof window === "undefined") return;
        const syncFromHash = () => {
            setViewMode(readViewMode());
            setPendingFocusId(readFocusId());
        };
        syncFromHash();
        return onHashChange(syncFromHash);
    }, []);

    const handleViewModeChange = useCallback((mode: ViewMode) => {
        setViewMode(mode);
        writeViewMode(mode);
    }, []);

    const handleFocusOnMap = useCallback((id: string) => {
        writeViewMode("map");
        writeFocusId(id);
        setViewMode("map");
        setPendingFocusId(id);
    }, []);

    const handleFocusConsumed = useCallback(() => {
        setPendingFocusId(null);
        clearFocusId();
    }, []);

    // Search + filter with debounce and session cache
    const { filtered, suggestions } = useSearch({
        dataset: globalLocations,
        search: filters.search,
        category: filters.category,
        debounceMs: 350,
        cacheSize: 30,
    });

    // Compute empty state conditions
    const hasCategoryFilter = filters.category && filters.category !== "all";
    const hasSearchQuery = filters.search.trim().length > 0;
    const hasActiveSearch = hasSearchQuery || hasCategoryFilter;

    // Load locations based on viewport bbox
    const suppressNextViewportFetch = useCallback(() => {
        suppressNextViewportFetchRef.current = true;
    }, []);

    useEffect(() => {
        const nextBbox = viewportBbox ?? null;

        // Skip viewport fetch if no bbox (global fetch handles this case)
        if (!nextBbox) {
            return;
        }

        if (debounceTimeoutRef.current !== null) {
            window.clearTimeout(debounceTimeoutRef.current);
            debounceTimeoutRef.current = null;
        }

        if (suppressNextViewportFetchRef.current) {
            suppressNextViewportFetchRef.current = false;
            return;
        }

        // Skip scheduling if an identical request already settled and no in-flight request exists
        if (hasSettledRef.current && lastSettledBboxRef.current === nextBbox && !inFlightRequestRef.current) {
            return;
        }

        // Skip if identical request already in-flight
        if (inFlightRequestRef.current && inFlightRequestRef.current.bbox === nextBbox) {
            return;
        }

        let cancelled = false;

        debounceTimeoutRef.current = window.setTimeout(() => {
            if (cancelled) return;

            const previous = inFlightRequestRef.current;
            if (previous) {
                previous.controller.abort();
            }

            const controller = new AbortController();
            const requestBbox = nextBbox;
            inFlightRequestRef.current = { bbox: requestBbox, controller };

            setLoading(true);
            setError(null);

            const load = async () => {
                try {
                    // Viewport fetch only handles bbox-based requests (global fetch is separate)
                    // requestBbox should never be null here due to early return in useEffect
                    const rows = await fetchLocations(requestBbox, 1000, 0, controller.signal);
                    if (controller.signal.aborted || cancelled) return;

                    if (import.meta.env.DEV) {
                        // console.debug(`[MapTab] Fetched ${rows.length} locations for bbox: ${requestBbox}`);
                    }

                    setViewportLocations(rows);

                    if (controller.signal.aborted || cancelled) return;
                    lastSettledBboxRef.current = requestBbox;
                    hasSettledRef.current = true;
                } catch (e: any) {
                    if (controller.signal.aborted || cancelled) {
                        return;
                    }
                    setError(e instanceof Error ? e.message : "Onbekende fout");
                } finally {
                    if (controller.signal.aborted || cancelled) return;
                    if (inFlightRequestRef.current?.controller === controller) {
                        inFlightRequestRef.current = null;
                    }
                    setLoading(false);
                }
            };

            void load();
        }, 200);

        return () => {
            cancelled = true;
            if (debounceTimeoutRef.current !== null) {
                window.clearTimeout(debounceTimeoutRef.current);
                debounceTimeoutRef.current = null;
            }
        };
    }, [viewportBbox]);

    useEffect(() => {
        return () => {
            if (debounceTimeoutRef.current !== null) {
                window.clearTimeout(debounceTimeoutRef.current);
                debounceTimeoutRef.current = null;
            }
            if (inFlightRequestRef.current) {
                inFlightRequestRef.current.controller.abort();
                inFlightRequestRef.current = null;
            }
        };
    }, []);

    // Fetch global categories on mount (independent of viewport)
    useEffect(() => {
        let cancelled = false;
        const controller = new AbortController();

        async function loadCategories() {
            setCategoriesLoading(true);
            setCategoriesError(null);
            try {
                const result = await fetchCategories(controller.signal);
                if (cancelled) return;
                setGlobalCategories(result);
            } catch (e: any) {
                if (cancelled) return;
                console.error("[MapTab] Failed to load categories", e);
                setCategoriesError(e instanceof Error ? e.message : "Failed to load categories");
                // Do NOT throw; fall back to dynamic/KNOWN_CATEGORIES
            } finally {
                if (cancelled) return;
                setCategoriesLoading(false);
            }
        }

        void loadCategories();

        return () => {
            cancelled = true;
            controller.abort();
        };
    }, []);

    // Fetch global locations on mount (independent of viewport)
    useEffect(() => {
        let cancelled = false;
        const controller = new AbortController();

        async function loadGlobalLocations() {
            setGlobalLocationsLoading(true);
            setGlobalLocationsError(null);
            try {
                const totalCount = await fetchLocationsCount(null, controller.signal);
                if (controller.signal.aborted || cancelled) return;

                const allLocations: LocationMarker[] = [];
                const pageSize = 10000;
                let offset = 0;

                while (offset < totalCount) {
                    if (controller.signal.aborted || cancelled) return;
                    const page = await fetchLocations(null, pageSize, offset, controller.signal);
                    allLocations.push(...page);
                    if (page.length < pageSize) {
                        break;
                    }
                    offset += pageSize;
                }

                if (controller.signal.aborted || cancelled) return;
                setGlobalLocations(allLocations);
            } catch (e: any) {
                if (controller.signal.aborted || cancelled) return;
                setGlobalLocationsError(e instanceof Error ? e.message : "Failed to load locations");
            } finally {
                if (cancelled) return;
                setGlobalLocationsLoading(false);
            }
        }

        void loadGlobalLocations();

        return () => {
            cancelled = true;
            controller.abort();
        };
    }, []);

    // Dynamic categories from current viewport (fallback)
    const dynamicCategoryOptions = useMemo(() => {
        const map = new Map<string, string>();
        for (const l of viewportLocations) {
            const key = (l.category_key ?? l.category ?? "").toLowerCase();
            if (!key || key === "other") continue;
            const label = l.category_label || key;
            if (!map.has(key)) {
                map.set(key, label);
            }
        }
        return Array.from(map.entries())
            .sort((a, b) => a[0].localeCompare(b[0], "en"))
            .map(([key, label]) => ({ key, label }));
    }, [viewportLocations]);

    // Prefer global categories, fall back to dynamic
    const categoryOptions = useMemo(() => {
        // 1) Prefer global categories when available
        if (globalCategories.length > 0) {
            return [...globalCategories];
        }
        // 2) Fall back to dynamic options from current viewport
        if (dynamicCategoryOptions.length > 0) {
            return [...dynamicCategoryOptions];
        }
        // 3) Absolute last fallback handled in Filters.tsx (KNOWN_CATEGORIES)
        return [];
    }, [globalCategories, dynamicCategoryOptions]);

    // Huidige selectie-object
    const highlighted = useMemo(() => filtered.find((l) => l.id === highlightedId) ?? null, [filtered, highlightedId]);
    const detail = useMemo(() => filtered.find((l) => l.id === effectiveDetailId) ?? null, [filtered, effectiveDetailId]);

    const handleHighlight = (id: string | null) => {
        navigationActions.setMap({ selectedLocationId: id });
    };

    const handleOpenDetail = (id: string) => {
        navigationActions.setMap({ selectedLocationId: id });
        setDetailIdLocal(id);
    };

    const handleCloseDetail = () => {
        setDetailIdLocal(null);
    };

    // Note dialog handlers
    const handleAddNote = () => {
        setEditingNote(null);
        setIsNoteDialogOpen(true);
    };

    const handleEditNote = (note: NoteResponse) => {
        setEditingNote(note);
        setIsNoteDialogOpen(true);
    };

    const handleSaveNote = async (content: string) => {
        if (!detail) return;

        try {
            const locationId = parseInt(detail.id);
            if (editingNote) {
                await updateNote(editingNote.id, content);
                toast.success("Notitie bijgewerkt");
            } else {
                await createNote(locationId, content);
                toast.success("Notitie toegevoegd");
            }

            setIsNoteDialogOpen(false);
            setEditingNote(null);
            // Notes will be refreshed by UnifiedLocationDetail's useEffect when it re-renders
        } catch (error: any) {
            throw error;
        }
    };

    const handleNotesRefresh = () => {
        // Trigger a re-render of UnifiedLocationDetail by toggling detailId
        // This is a workaround - ideally we'd have a proper refresh mechanism
        if (detailIdLocal) {
            const currentId = detailIdLocal;
            setDetailIdLocal(null);
            setTimeout(() => setDetailIdLocal(currentId), 0);
        }
    };

    const handleFiltersChange = (patch: Partial<typeof filters>) => {
        navigationActions.setMap({
            filters: { ...filters, ...patch }
        });
    };

    const handleScrollPositionChange = useCallback((scrollTop: number) => {
        navigationActions.setMap({ listScrollTop: scrollTop });
    }, []);

    // Restore scroll position on mount (for list view)
    useEffect(() => {
        if (viewMode !== "list" || scrollRestoredRef.current || !listScrollContainerRef.current) {
            return;
        }

        const scrollTop = mapNavigation.listScrollTop;
        if (scrollTop > 0) {
            requestAnimationFrame(() => {
                if (listScrollContainerRef.current && !scrollRestoredRef.current) {
                    listScrollContainerRef.current.scrollTo({ top: scrollTop, behavior: "auto" });
                    scrollRestoredRef.current = true;
                }
            });
        } else {
            scrollRestoredRef.current = true;
        }
    }, [viewMode, mapNavigation.listScrollTop]);

    // Track scroll position changes (for list view)
    useEffect(() => {
        if (viewMode !== "list") {
            scrollRestoredRef.current = false;
            return;
        }

        const container = listScrollContainerRef.current;
        if (!container || !handleScrollPositionChange) return;

        const handleScroll = () => {
            if (scrollThrottleRef.current !== null) {
                window.cancelAnimationFrame(scrollThrottleRef.current);
            }

            scrollThrottleRef.current = window.requestAnimationFrame(() => {
                if (container) {
                    handleScrollPositionChange(container.scrollTop);
                }
            });
        };

        container.addEventListener("scroll", handleScroll, { passive: true });

        return () => {
            container.removeEventListener("scroll", handleScroll);
            if (scrollThrottleRef.current !== null) {
                window.cancelAnimationFrame(scrollThrottleRef.current);
                scrollThrottleRef.current = null;
            }
        };
    }, [viewMode, handleScrollPositionChange]);

    const renderFilters = (idPrefixOverride?: string) => (
        <Filters
            search={filters.search}
            category={filters.category}
            loading={loading}
            categoryOptions={categoryOptions}
            suggestions={suggestions}
            idPrefix={idPrefixOverride ?? (isDesktop ? "desktop" : "mobile")}
            onChange={handleFiltersChange}
            viewMode={viewMode}
            onViewModeChange={handleViewModeChange}
        />
    );

    useEffect(() => {
        if (!hasAppliedInitialFocusRef.current) {
            hasAppliedInitialFocusRef.current = true;
            return;
        }
        if (viewMode === "map") {
            const target = mapHeadingRef.current;
            if (!target) return;
            const frame = requestAnimationFrame(() => {
                target.focus({ preventScroll: true });
            });
            return () => cancelAnimationFrame(frame);
        }
        // For list view, focus is handled by the AppHeader or filters
    }, [viewMode]);

    const listViewDesktop = (
        <div className="flex flex-col h-full relative">
            {/* Red gradient overlay */}
            <div
                className="absolute inset-x-0 top-0 pointer-events-none z-0"
                style={{
                    height: '25%',
                    background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
                }}
            />
            <AppHeader onNotificationClick={() => { }} />
            <div
                ref={listScrollContainerRef}
                className="flex h-full w-full flex-col gap-3 flex-1 overflow-y-auto px-4 pb-24 text-foreground focus:outline-none relative z-10"
                role="region"
                aria-label="Locatielijst"
                data-view="list"
            >
                {renderFilters("list-desktop")}
                <LocationList
                    locations={filtered}
                    selectedId={highlightedId}
                    onSelect={handleHighlight}
                    onSelectDetail={handleOpenDetail}
                    onShowOnMap={handleFocusOnMap}
                    autoScrollToSelected
                    isLoading={globalLocationsLoading}
                    error={globalLocationsError}
                    hasActiveSearch={hasActiveSearch}
                />
            </div>
        </div>
    );

    const listViewMobile = (
        <div className="flex flex-col h-full relative">
            {/* Red gradient overlay */}
            <div
                className="absolute inset-x-0 top-0 pointer-events-none z-0"
                style={{
                    height: '25%',
                    background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
                }}
            />
            <AppHeader onNotificationClick={() => { }} />
            <div
                ref={listScrollContainerRef}
                className="flex h-full w-full flex-col gap-3 flex-1 overflow-y-auto px-4 pb-24 text-foreground focus:outline-none relative z-10"
                role="region"
                aria-label="Locatielijst"
                data-view="list"
            >
                {renderFilters("list-mobile")}
                {detail ? (
                    <UnifiedLocationDetail
                        location={detail}
                        viewMode="list"
                        onBack={() => {
                            setDetailIdLocal(null);
                            navigationActions.setMap({ selectedLocationId: null });
                        }}
                    />
                ) : (
                    <LocationList
                        locations={filtered}
                        selectedId={highlightedId}
                        onSelect={handleHighlight}
                        onSelectDetail={handleOpenDetail}
                        onShowOnMap={handleFocusOnMap}
                        autoScrollToSelected
                        isLoading={globalLocationsLoading}
                        error={globalLocationsError}
                        hasActiveSearch={hasActiveSearch}
                    />
                )}
            </div>
        </div>
    );

    const mapView = (
        <div
            className="relative h-full w-full overflow-hidden focus:outline-none"
            role="region"
            aria-labelledby={mapHeadingId}
            data-view="map"
        >
            <h2
                id={mapHeadingId}
                ref={mapHeadingRef}
                tabIndex={-1}
                className="sr-only"
            >
                Kaartweergave
            </h2>
            <MapView
                locations={filtered}
                globalLocations={globalLocations}
                highlightedId={highlightedId}
                detailId={effectiveDetailId}
                interactionDisabled={Boolean(detail)}
                onHighlight={handleHighlight}
                onOpenDetail={handleOpenDetail}
                onMapClick={() => {
                    handleHighlight(null);
                    handleCloseDetail();
                }}
                focusId={pendingFocusId}
                onFocusConsumed={handleFocusConsumed}
                centerOnSelect={false}
                onViewportChange={(bbox) => {
                    setViewportBbox(bbox);
                }}
                onSuppressNextViewportFetch={suppressNextViewportFetch}
            />
            <div className="hidden" aria-hidden>
                {renderFilters("map-overlay")}
            </div>
            {/* Top overlay - Search + Categories */}
            <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex justify-center px-4 pt-[var(--top-offset)]">
                <div className="pointer-events-auto w-full max-w-2xl flex flex-col gap-3" data-filters-overlay>
                    <FloatingSearchBar
                        value={filters.search}
                        onValueChange={(next) => handleFiltersChange({ search: next })}
                        onClear={() => handleFiltersChange({ search: "" })}
                        suggestions={suggestions}
                        loading={loading}
                        ariaLabel="Zoek locaties"
                    />
                    <CategoryChips
                        categories={categoryOptions}
                        activeCategory={filters.category}
                        onSelect={(key) => handleFiltersChange({ category: key })}
                    />
                </div>
            </div>
            {/* Bottom overlay - Map/List toggle */}
            <div
                className="pointer-events-none fixed inset-x-0 z-20 flex justify-center px-4"
                style={{ bottom: "var(--bottom-offset)" }}
            >
                <div className="pointer-events-auto">
                    <MapListToggle
                        viewMode={viewMode}
                        onViewModeChange={handleViewModeChange}
                    />
                </div>
            </div>
            {loading && (
                <div className="absolute top-4 right-4 z-10 rounded-3xl border border-border bg-card px-4 py-2 text-sm text-foreground shadow-soft">
                    Locaties worden geladen…
                </div>
            )}
        </div>
    );

    return (
        <ViewportProvider>
            <AppViewportShell
                variant="map"
                data-route-viewport
            >
                {viewMode === "map"
                    ? mapView
                    : (isCompact ? listViewMobile : listViewDesktop)}

                {detail && (isDesktop || viewMode === "map") && (
                    <UnifiedLocationDetail
                        location={detail}
                        viewMode="map"
                        open={Boolean(detail)}
                        onBack={handleCloseDetail}
                        onClose={handleCloseDetail}
                        onAddNote={handleAddNote}
                        onEditNote={handleEditNote}
                        onNotesRefresh={handleNotesRefresh}
                    />
                )}

                {/* Note Dialog - rendered outside UnifiedLocationDetail to avoid nesting issues */}
                {detail && (
                    <NoteDialog
                        open={isNoteDialogOpen}
                        onOpenChange={setIsNoteDialogOpen}
                        onSubmit={handleSaveNote}
                        initialContent={editingNote?.content || ""}
                        locationName={detail.name}
                    />
                )}
            </AppViewportShell>
        </ViewportProvider>
    );
}



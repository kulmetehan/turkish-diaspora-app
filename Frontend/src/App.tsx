// src/App.tsx
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import Filters from "@/components/Filters";
import { Icon } from "@/components/Icon";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import { ViewportProvider } from "@/contexts/viewport";
import OverlayDetailCard from "@/components/OverlayDetailCard";
import { CategoryChips } from "@/components/search/CategoryChips";
import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";
import { clearFocusId, onHashChange, readFocusId, readViewMode, writeFocusId, writeViewMode, type ViewMode } from "@/lib/routing/viewMode";

import { fetchLocations, fetchLocationsCount, fetchCategories, type LocationMarker, type CategoryOption } from "@/api/fetchLocations";

function HomePage() {
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

  // UI-filters (komen overeen met Filters.tsx props)
  const [filters, setFilters] = useState({
    search: "",
    category: "all",
    onlyTurkish: true, // UI-only; API already filters
  });

  // Geselecteerde locatie-id (sync met lijst + kaart)
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);

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
  const listHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const hasAppliedInitialFocusRef = useRef(false);
  const mapHeadingId = useId();
  const listHeadingId = useId();

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

  // Debug logging removed for production noise reduction

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
            console.debug(`[App] Fetched ${rows.length} locations for bbox: ${requestBbox}`);
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
        console.error("[App] Failed to load categories", e);
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
  const detail = useMemo(() => filtered.find((l) => l.id === detailId) ?? null, [filtered, detailId]);

  const handleHighlight = (id: string | null) => {
    setHighlightedId(id);
  };

  const handleOpenDetail = (id: string) => {
    setHighlightedId(id);
    setDetailId(id);
  };

  const handleCloseDetail = () => {
    setDetailId(null);
  };

  const renderFilters = (idPrefixOverride?: string) => (
    <Filters
      search={filters.search}
      category={filters.category}
      onlyTurkish={filters.onlyTurkish}
      loading={loading}
      categoryOptions={categoryOptions}
      suggestions={suggestions}
      idPrefix={idPrefixOverride ?? (isDesktop ? "desktop" : "mobile")}
      onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
      viewMode={viewMode}
      onViewModeChange={handleViewModeChange}
    />
  );

  useEffect(() => {
    if (!hasAppliedInitialFocusRef.current) {
      hasAppliedInitialFocusRef.current = true;
      return;
    }
    const target = viewMode === "map" ? mapHeadingRef.current : listHeadingRef.current;
    if (!target) return;
    const frame = requestAnimationFrame(() => {
      target.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [viewMode]);

  const listViewDesktop = (
    <div
      className="mx-auto flex h-full w-full max-w-4xl flex-col gap-4 overflow-hidden rounded-[32px] border border-white/10 bg-surface-raised/70 px-4 py-5 text-foreground shadow-soft backdrop-blur-xl focus:outline-none"
      role="region"
      aria-labelledby={listHeadingId}
      data-view="list"
    >
      <h2
        id={listHeadingId}
        ref={listHeadingRef}
        tabIndex={-1}
        className="text-lg font-semibold text-foreground"
      >
        Locatielijst
      </h2>
      {renderFilters("list-desktop")}
      <div className="flex-1 overflow-hidden">
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
          fullHeight
        />
      </div>
    </div>
  );

  const listViewMobile = (
    <div
      className="flex h-full w-full flex-col gap-4 overflow-hidden rounded-[28px] border border-white/10 bg-surface-raised/70 px-4 py-5 text-foreground shadow-soft backdrop-blur-xl focus:outline-none"
      role="region"
      aria-labelledby={listHeadingId}
      data-view="list"
    >
      <h2
        id={listHeadingId}
        ref={listHeadingRef}
        tabIndex={-1}
        className="text-lg font-semibold text-foreground"
      >
        Locatielijst
      </h2>
      {renderFilters("list-mobile")}
      <div className="flex-1 overflow-hidden">
        {detail ? (
          <div className="h-full overflow-auto">
            <LocationDetail
              location={detail}
              onBackToList={() => {
                setDetailId(null);
                setHighlightedId(null);
              }}
            />
          </div>
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
            fullHeight
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
        detailId={detailId}
        interactionDisabled={Boolean(detail)}
        onHighlight={handleHighlight}
        onOpenDetail={handleOpenDetail}
        onMapClick={() => {
          handleHighlight(null);
          handleCloseDetail();
        }}
        focusId={pendingFocusId}
        onFocusConsumed={handleFocusConsumed}
        onViewportChange={(bbox) => {
          setViewportBbox(bbox);
        }}
        onSuppressNextViewportFetch={suppressNextViewportFetch}
      />
      <div className="hidden" aria-hidden>
        {renderFilters("map-overlay")}
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex justify-center px-4 pt-[var(--top-offset)]">
        <div className="pointer-events-auto w-full max-w-2xl" data-filters-overlay>
          <div className="flex flex-col gap-3 rounded-[32px] border border-border bg-card p-4 text-foreground shadow-card supports-[backdrop-filter]:backdrop-blur-2xl">
            <Tabs
              value={viewMode}
              onValueChange={(value) => {
                if (value === viewMode) return;
                if (value === "list" || value === "map") {
                  handleViewModeChange(value);
                }
              }}
            >
              <TabsList className="grid w-full grid-cols-2 rounded-2xl border border-border bg-surface-muted p-1 text-xs	font-semibold uppercase tracking-wide text-muted-foreground sm:text-sm shadow-inner">
                <TabsTrigger
                  value="map"
                  data-view="map"
                  className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm text-foreground data-[state=active]:bg-[hsl(var(--brand-red-strong))] data-[state=active]:text-brand-white data-[state=active]:shadow-[0_12px_30px_rgba(0,0,0,0.35)]"
                  onClick={() => {
                    if (viewMode !== "map") {
                      handleViewModeChange("map");
                    }
                  }}
                >
                  <Icon name="Map" className="h-4 w-4" aria-hidden />
                  Kaart
                </TabsTrigger>
                <TabsTrigger
                  value="list"
                  data-view="list"
                  className="flex items-center justify-center gap-2 rounded-xl py-2 text-sm text-foreground data-[state=active]:bg-[hsl(var(--brand-red-strong))] data-[state=active]:text-brand-white data-[state=active]:shadow-[0_12px_30px_rgba(0,0,0,0.35)]"
                  onClick={() => {
                    if (viewMode !== "list") {
                      handleViewModeChange("list");
                    }
                  }}
                >
                  <Icon name="List" className="h-4 w-4" aria-hidden />
                  Lijst
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <FloatingSearchBar
              value={filters.search}
              onValueChange={(next) => setFilters((prev) => ({ ...prev, search: next }))}
              onClear={() => setFilters((prev) => ({ ...prev, search: "" }))}
              suggestions={suggestions}
              loading={loading}
              ariaLabel="Zoek locaties"
            />
            <CategoryChips
              categories={categoryOptions}
              activeCategory={filters.category}
              onSelect={(key) => setFilters((prev) => ({ ...prev, category: key }))}
            />
          </div>
        </div>
      </div>
      {loading && (
        <div className="absolute top-4 right-4 z-10 rounded-2xl border border-white/10 bg-surface-raised/85 px-4 py-2 text-sm text-brand-white shadow-soft">
          Loading locations...
        </div>
      )}
    </div>
  );

  return (
    <ViewportProvider>
      <div
        data-route-viewport
        className="relative h-[calc(100svh-var(--footer-height))] overflow-hidden bg-brand-surface-alt shadow-inner"
      >
        {viewMode === "map"
          ? mapView
          : (isCompact ? listViewMobile : listViewDesktop)}

        {detail && (isDesktop || viewMode === "map") && (
          <OverlayDetailCard
            location={detail}
            open={Boolean(detail)}
            onClose={handleCloseDetail}
          />
        )}
      </div>
    </ViewportProvider>
  );
}

export default HomePage;
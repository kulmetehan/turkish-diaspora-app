// src/App.tsx
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import Filters from "@/components/Filters";
import { Icon } from "@/components/Icon";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import OverlayDetailCard from "@/components/OverlayDetailCard";
import { CategoryChips } from "@/components/search/CategoryChips";
import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";
import { clearFocusId, onHashChange, readFocusId, readViewMode, writeFocusId, writeViewMode, type ViewMode } from "@/lib/routing/viewMode";

import { fetchLocations, fetchLocationsCount, type LocationMarker } from "@/api/fetchLocations";

function HomePage() {
  const [all, setAll] = useState<LocationMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewportBbox, setViewportBbox] = useState<string | null>(null);
  const debounceTimeoutRef = useRef<number | null>(null);

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
    locations: all,
    search: filters.search,
    category: filters.category,
    debounceMs: 350,
    cacheSize: 30,
  });

  // Load locations based on viewport bbox
  const suppressNextViewportFetch = useCallback(() => {
    suppressNextViewportFetchRef.current = true;
  }, []);

  useEffect(() => {
    const nextBbox = viewportBbox ?? null;

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
          if (!requestBbox) {
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
            setAll(allLocations);
          } else {
            const rows = await fetchLocations(requestBbox, 1000, 0, controller.signal);
            if (controller.signal.aborted || cancelled) return;

            if (import.meta.env.DEV) {
              console.debug(`[App] Fetched ${rows.length} locations for bbox: ${requestBbox}`);
            }

            setAll(rows);
          }

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

  // filtered comes from useSearch; keep API order (no client sorting)
  // Build category options from data (canonical key + label)
  const categoryOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const l of all) {
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
  }, [all]);

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
      className="mx-auto flex h-full w-full max-w-4xl flex-col gap-4 overflow-hidden px-4 py-4 focus:outline-none"
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
          emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
          fullHeight
        />
      </div>
    </div>
  );

  const listViewMobile = (
    <div
      className="flex h-full w-full flex-col gap-4 overflow-hidden px-4 py-4 focus:outline-none"
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
            emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
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
          <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-background/95 p-4 shadow-2xl supports-[backdrop-filter]:bg-background/80">
            <Tabs
              value={viewMode}
              onValueChange={(value) => {
                if (value === viewMode) return;
                if (value === "list" || value === "map") {
                  handleViewModeChange(value);
                }
              }}
            >
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger
                  value="map"
                  data-view="map"
                  className="flex items-center justify-center gap-2 text-sm"
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
                  className="flex items-center justify-center gap-2 text-sm"
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
        <div className="absolute top-4 right-4 z-10 rounded-md bg-white/90 px-4 py-2 text-sm shadow-md">
          Loading locations...
        </div>
      )}
    </div>
  );

  return (
    <div
      data-route-viewport
      className="relative h-[calc(100svh-var(--footer-height))] overflow-hidden"
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
  );
}

export default HomePage;
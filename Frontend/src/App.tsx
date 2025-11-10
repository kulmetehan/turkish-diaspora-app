// src/App.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import BottomSheet, { type SnapPoint } from "@/components/BottomSheet";
import Filters from "@/components/Filters";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import OverlayDetailCard from "@/components/OverlayDetailCard";
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
  const [sheetSnapPoint, setSheetSnapPoint] = useState<SnapPoint>("half");
  const [isSheetOpen, setIsSheetOpen] = useState(true);

  // Responsive breakpoint detection
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    if (typeof window === "undefined") return "map";
    return readViewMode();
  });
  const [pendingFocusId, setPendingFocusId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return readFocusId();
  });
  const inFlightRequestRef = useRef<{ bbox: string | null; controller: AbortController } | null>(null);
  const lastSettledBboxRef = useRef<string | null>(null);
  const hasSettledRef = useRef(false);

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
  useEffect(() => {
    const nextBbox = viewportBbox ?? null;

    if (debounceTimeoutRef.current !== null) {
      window.clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = null;
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
    if (id && !isDesktop) {
      setSheetSnapPoint("collapsed");
    }
  };

  const handleOpenDetail = (id: string) => {
    setHighlightedId(id);
    setDetailId(id);
    if (!isDesktop) {
      setSheetSnapPoint("collapsed");
    }
  };

  const handleCloseDetail = () => {
    setDetailId(null);
    if (!isDesktop) {
      setSheetSnapPoint("half");
    }
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

  const listViewDesktop = (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-4 min-h-[calc(100dvh-56px)]">
      {renderFilters("list-desktop")}
      <div className="flex-1">
        <LocationList
          locations={filtered}
          selectedId={highlightedId}
          onSelect={handleHighlight}
          onSelectDetail={handleOpenDetail}
          onShowOnMap={handleFocusOnMap}
          autoScrollToSelected
          emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
        />
      </div>
    </div>
  );

  const listViewMobile = (
    <div className="lg:hidden">
      <BottomSheet
        open={isSheetOpen}
        snapPoint={sheetSnapPoint}
        onSnapPointChange={setSheetSnapPoint}
        onClose={() => setIsSheetOpen(false)}
      >
        {highlightedId && highlighted ? (
          <LocationDetail
            location={highlighted}
            onBackToList={() => handleHighlight(null)}
          />
        ) : (
          <div className="flex h-full flex-col gap-3">
            {renderFilters("list-mobile")}
            <div className="flex-1 overflow-auto">
              <LocationList
                locations={filtered}
                selectedId={highlightedId}
                onSelect={handleHighlight}
                onSelectDetail={handleOpenDetail}
                onShowOnMap={handleFocusOnMap}
                autoScrollToSelected
                emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
              />
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  );

  const mapView = (
    <div className="relative h-[calc(100dvh-56px)] w-full">
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
      />
      <div className="pointer-events-none absolute left-1/2 top-4 z-10 flex w-full max-w-xl -translate-x-1/2 px-4">
        <div className="pointer-events-auto w-full" data-filters-overlay>
          {renderFilters("map")}
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
    <div className="relative min-h-[calc(100dvh-56px)]">
      {viewMode === "map"
        ? mapView
        : (isDesktop ? listViewDesktop : listViewMobile)}

      {detail && (
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
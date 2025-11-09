// src/App.tsx
import { useEffect, useMemo, useRef, useState } from "react";

import BottomSheet, { type SnapPoint } from "@/components/BottomSheet";
import Filters from "@/components/Filters";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import OverlayDetailCard from "@/components/OverlayDetailCard";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";

import { fetchLocations, fetchLocationsCount, type LocationMarker } from "@/api/fetchLocations";

function HomePage() {
  const [all, setAll] = useState<LocationMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewportBbox, setViewportBbox] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
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

  // Debug logging removed for production noise reduction

  // Search + filter with debounce and session cache
  const { debouncedQuery, filtered, suggestions } = useSearch({
    locations: all,
    search: filters.search,
    category: filters.category,
    debounceMs: 350,
    cacheSize: 30,
  });

  // Load locations based on viewport bbox
  useEffect(() => {
    let alive = true;

    if (debounceTimeoutRef.current !== null) {
      window.clearTimeout(debounceTimeoutRef.current);
      debounceTimeoutRef.current = null;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    debounceTimeoutRef.current = window.setTimeout(() => {
      setLoading(true);
      setError(null);

      const load = async () => {
        try {
          if (!viewportBbox) {
            const totalCount = await fetchLocationsCount(null, abortController.signal);

            if (!alive || abortController.signal.aborted) return;

            const allLocations: LocationMarker[] = [];
            const pageSize = 10000;
            let offset = 0;

            while (offset < totalCount) {
              if (!alive || abortController.signal.aborted) return;

              const page = await fetchLocations(null, pageSize, offset, abortController.signal);
              allLocations.push(...page);

              if (page.length < pageSize) {
                break;
              }

              offset += pageSize;
            }

            if (!alive || abortController.signal.aborted) return;
            setAll(allLocations);
          } else {
            const rows = await fetchLocations(viewportBbox, 1000, 0, abortController.signal);

            if (!alive || abortController.signal.aborted) return;

            if (import.meta.env.DEV) {
              console.debug(`[App] Fetched ${rows.length} locations for bbox: ${viewportBbox}`);
            }

            setAll(rows);
          }
        } catch (e: any) {
          if (e?.name === "AbortError" || abortController.signal.aborted) {
            return;
          }
          if (!alive) return;
          setError(e instanceof Error ? e.message : "Onbekende fout");
        } finally {
          if (!alive || abortController.signal.aborted) return;
          setLoading(false);
        }
      };

      void load();
    }, 200);

    return () => {
      alive = false;
      if (debounceTimeoutRef.current !== null) {
        window.clearTimeout(debounceTimeoutRef.current);
        debounceTimeoutRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [viewportBbox]);

  // filtered comes from useSearch; keep API order (no client sorting)
  // Build category options from data (canonical key + label)
  const categoryOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const l of all) {
      const key = (l.category_key ?? l.category ?? "").toLowerCase();
      if (!key || key === "other") continue;
      const label = l.category_label || key;
      if (!map.has(key)) map.set(key, label);
    }
    return Array.from(map.entries()).map(([key, label]) => ({ key, label }));
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

  return (
    <div className="relative min-h-[calc(100dvh-56px)] lg:grid lg:grid-cols-2">
      {/* Left panel (filters + list) - desktop only */}
      <aside className="hidden lg:flex lg:flex-col border-r bg-background">
        <div className="p-3 border-b">
          <Filters
            search={filters.search}
            category={filters.category}
            onlyTurkish={filters.onlyTurkish}
            loading={loading}
            categoryOptions={categoryOptions}
            suggestions={suggestions}
            idPrefix="desktop"
            onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
          />
        </div>
        <div className="overflow-auto flex-1">
          <LocationList
            locations={filtered}
            selectedId={highlightedId}
            onSelect={handleHighlight}
            onSelectDetail={handleOpenDetail}
            autoScrollToSelected
            emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
          />
        </div>
      </aside>

      {/* Map panel (always rendered) */}
      <main className="fixed inset-0 h-screen w-screen z-0 lg:static lg:h-auto lg:w-auto lg:flex-1">
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
          onViewportChange={(bbox) => {
            setViewportBbox(bbox);
          }}
        />
        {/* Loading indicator */}
        {loading && (
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white/90 px-4 py-2 rounded-md shadow-md text-sm z-10">
            Loading locations...
          </div>
        )}
      </main>

      {/* BottomSheet mobile overlay (list/detail UI) - mobile only */}
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
            <div className="flex flex-col h-full">
              <div className="p-3 border-b">
                <Filters
                  search={filters.search}
                  category={filters.category}
                  onlyTurkish={filters.onlyTurkish}
                  loading={loading}
                  categoryOptions={categoryOptions}
                  suggestions={suggestions}
                  idPrefix="mobile"
                  onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
                />
              </div>
              <div className="overflow-auto flex-1">
                <LocationList
                  locations={filtered}
                  selectedId={highlightedId}
                  onSelect={handleHighlight}
                  onSelectDetail={handleOpenDetail}
                  autoScrollToSelected
                  emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
                />
              </div>
            </div>
          )}
        </BottomSheet>
      </div>

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
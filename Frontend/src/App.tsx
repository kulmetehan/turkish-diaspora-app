// src/App.tsx
import { useEffect, useMemo, useRef, useState } from "react";

import BottomSheet, { type SnapPoint } from "@/components/BottomSheet";
import Filters from "@/components/Filters";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useSearch } from "@/hooks/useSearch";

import { fetchLocations, fetchLocationsCount, type LocationMarker } from "@/api/fetchLocations";

function HomePage() {
  const [all, setAll] = useState<LocationMarker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewportBbox, setViewportBbox] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // UI-filters (komen overeen met Filters.tsx props)
  const [filters, setFilters] = useState({
    search: "",
    category: "all",
    onlyTurkish: true, // UI-only; API already filters
  });

  // Geselecteerde locatie-id (sync met lijst + kaart)
  const [selectedId, setSelectedId] = useState<string | null>(null);

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
    
    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    setLoading(true);
    setError(null);
    
    const load = async () => {
      try {
        // If zoomed out (no bbox), fetch all locations with pagination
        if (!viewportBbox) {
          // First, get the total count
          const totalCount = await fetchLocationsCount(null, abortController.signal);
          
          if (!alive || abortController.signal.aborted) return;
          
          // Fetch all locations in pages if needed
          const allLocations: LocationMarker[] = [];
          const pageSize = 10000;
          let offset = 0;
          
          while (offset < totalCount) {
            if (!alive || abortController.signal.aborted) return;
            
            const page = await fetchLocations(null, pageSize, offset, abortController.signal);
            allLocations.push(...page);
            
            // If we got fewer results than requested, we've reached the end
            if (page.length < pageSize) {
              break;
            }
            
            offset += pageSize;
          }
          
          if (!alive || abortController.signal.aborted) return;
          setAll(allLocations);
        } else {
          // If bbox is provided, fetch locations within bbox
          // Use a reasonable limit for bbox queries (usually won't need pagination)
          const rows = await fetchLocations(viewportBbox, 1000, 0, abortController.signal);
          
          if (!alive || abortController.signal.aborted) return;
          setAll(rows);
        }
      } catch (e: any) {
        // Ignore AbortError (request was cancelled)
        if (e?.name === 'AbortError' || abortController.signal.aborted) {
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

    return () => {
      alive = false;
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
  const selected = useMemo(() => filtered.find((l) => l.id === selectedId) ?? null, [filtered, selectedId]);

  // Calculate bottom sheet height for map panning
  const bottomSheetHeight = useMemo(() => {
    if (isDesktop) return 0;

    switch (sheetSnapPoint) {
      case "collapsed": return 96;
      case "half": return window.innerHeight * 0.55;
      case "full": return window.innerHeight * 0.92;
      default: return 96;
    }
  }, [isDesktop, sheetSnapPoint]);

  // Handle location selection - minimize sheet and show detail on mobile
  const handleLocationSelect = (id: string) => {
    setSelectedId(id);
    if (!isDesktop) {
      // On mobile: minimize sheet to show map with selected location
      setSheetSnapPoint("collapsed");
    }
  };

  // Handle map click - show list on mobile
  const handleMapClick = () => {
    if (!isDesktop) {
      setSelectedId(null); // Clear selection
      setSheetSnapPoint("half"); // Show list
    }
  };

  // Handle back to list from detail view
  const handleBackToList = () => {
    setSelectedId(null);
    if (!isDesktop) {
      // Return to list view (half height)
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
            onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
          />
        </div>
        <div className="overflow-auto flex-1">
          <LocationList
            locations={filtered}
            selectedId={selectedId}
            onSelect={(id) => setSelectedId(id)}
            autoScrollToSelected
            emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
          />
        </div>
      </aside>

      {/* Map panel (always rendered) */}
      <main className="fixed inset-0 h-screen w-screen z-0 lg:static lg:h-auto lg:w-auto lg:flex-1">
        <MapView
          locations={filtered}
          selectedId={selectedId}
          onSelect={(id) => { setSelectedId(id); if (!isDesktop) setSheetSnapPoint("collapsed"); }}
          onMapClick={() => {
            if (!isDesktop) {
              setSelectedId(null);
              setSheetSnapPoint("half");
            } else {
              setSelectedId(null);
            }
          }}
          onViewportChange={(bbox) => {
            setViewportBbox(bbox);
          }}
          bottomSheetHeight={isDesktop ? 0 : bottomSheetHeight}
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
          {selectedId && selected ? (
            <LocationDetail
              location={selected}
              onBackToList={handleBackToList}
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
                  onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
                />
              </div>
              <div className="overflow-auto flex-1">
                <LocationList
                  locations={filtered}
                  selectedId={selectedId}
                  onSelect={(id) => { setSelectedId(id); setSheetSnapPoint("collapsed"); }}
                  autoScrollToSelected
                  emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
                />
              </div>
            </div>
          )}
        </BottomSheet>
      </div>
    </div>
  );
}

export default HomePage;
// src/App.tsx
import { useEffect, useMemo, useState } from "react";

import BottomSheet, { type SnapPoint } from "@/components/BottomSheet";
import Filters from "@/components/Filters";
import LocationDetail from "@/components/LocationDetail";
import LocationList from "@/components/LocationList";
import MapView from "@/components/MapView";
import SortBar from "@/components/SortBar";
import { useMediaQuery } from "@/hooks/useMediaQuery";

import { fetchLocations, getCachedLocations, type Location } from "@/lib/api/location";

// Sorteersleutel zoals in jouw SortBar gebruikt
export type SortKey = "relevance" | "rating_desc" | "name_asc";

function HomePage() {
  const [all, setAll] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingCache, setUsingCache] = useState(false);

  // UI-filters (komen overeen met Filters.tsx props)
  const [filters, setFilters] = useState({
    search: "",
    category: "all",
    minRating: 0,
    onlyTurkish: true, // Keep for UI consistency, but API now returns only Turkish businesses
  });

  // Sorteerkeuze (komt overeen met SortBar props)
  const [sort, setSort] = useState<SortKey>("rating_desc");

  // Geselecteerde locatie-id (sync met lijst + kaart)
  const [selectedId, setSelectedId] = useState<number>(-1);

  // Bottom sheet state
  const [sheetSnapPoint, setSheetSnapPoint] = useState<SnapPoint>("half");
  const [isSheetOpen, setIsSheetOpen] = useState(true);

  // Responsive breakpoint detection
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  // Debug logging removed for production noise reduction

  // Debounced search value for smoother typing
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const handle = setTimeout(() => setDebouncedSearch(filters.search), 300);
    return () => clearTimeout(handle);
  }, [filters.search]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setUsingCache(false);

    const load = async () => {
      try {
        const rows = await fetchLocations();
        if (!alive) return;
        // If API returns empty but we have cached data, prefer cache and retry
        if (rows.length === 0) {
          const cached = getCachedLocations();
          if (cached && cached.length > 0) {
            setAll(cached);
            setUsingCache(true);
            setTimeout(async () => {
              try {
                const fresh = await fetchLocations();
                if (!alive) return;
                if (fresh.length > 0) {
                  setAll(fresh);
                  setUsingCache(false);
                  setError(null);
                }
              } catch { }
            }, 2000);
            return;
          }
        }
        setAll(rows);
      } catch (e: any) {
        if (!alive) return;
        // Try cached data as fallback
        const cached = getCachedLocations();
        if (cached && cached.length > 0) {
          setAll(cached);
          setUsingCache(true);
          // Silent retry after short delay to update live data if available
          setTimeout(async () => {
            try {
              const fresh = await fetchLocations();
              if (!alive) return;
              setAll(fresh);
              setUsingCache(false);
              setError(null);
            } catch { }
          }, 2000);
        } else {
          setError(e instanceof Error ? e.message : "Onbekende fout");
        }
      } finally {
        if (!alive) return;
        setLoading(false);
      }
    };

    void load();

    return () => {
      alive = false;
    };
  }, []);

  // Filteren
  const filtered = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    return all.filter((l) => {
      // Note: API now returns only Turkish businesses, so no need to filter by is_turkish
      if (filters.category !== "all" && (l.category ?? "").toLowerCase() !== filters.category) return false;
      if ((l.rating ?? 0) < filters.minRating) return false;
      if (q && !(`${l.name}`.toLowerCase().includes(q))) return false;
      return true;
    });
  }, [all, debouncedSearch, filters.category, filters.minRating]);

  // Sorteren
  const sorted = useMemo(() => {
    const arr = [...filtered];
    switch (sort) {
      case "name_asc":
        arr.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "rating_desc":
        arr.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
        break;
      case "relevance":
        // voorlopig: geen speciale sortering, laat filtered volgorde staan
        break;
    }
    return arr;
  }, [filtered, sort]);

  // Huidige selectie-object
  const selected = useMemo(() => sorted.find((l) => l.id === selectedId) ?? null, [sorted, selectedId]);

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
  const handleLocationSelect = (id: number) => {
    setSelectedId(id);
    if (!isDesktop) {
      // On mobile: minimize sheet to show map with selected location
      setSheetSnapPoint("collapsed");
    }
  };

  // Handle map click - show list on mobile
  const handleMapClick = () => {
    if (!isDesktop) {
      setSelectedId(-1); // Clear selection
      setSheetSnapPoint("half"); // Show list
    }
  };

  // Handle back to list from detail view
  const handleBackToList = () => {
    setSelectedId(-1);
    if (!isDesktop) {
      // Return to list view (half height)
      setSheetSnapPoint("half");
    }
  };

  if (isDesktop) {
    // Desktop layout: side-by-side
    return (
      <div className="flex flex-col lg:grid lg:grid-cols-2 gap-0 min-h-[calc(100dvh-56px)]">
        {/* Linker kolom: lijst en filters */}
        <aside className="border-r bg-background lg:order-1 order-1 lg:h-auto h-[40vh] flex flex-col">
          <div className="p-3 border-b">
            <Filters
              search={filters.search}
              category={filters.category}
              minRating={filters.minRating}
              onlyTurkish={filters.onlyTurkish}
              loading={loading}
              onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
            />
          </div>

          {usingCache && (
            <div className="px-3 py-2 text-xs text-muted-foreground">
              Showing cached data; retrying in background…
            </div>
          )}
          <div className="p-3 border-b">
            <SortBar sort={sort} onChange={(key) => setSort(key)} total={sorted.length} />
          </div>

          <div className="overflow-auto flex-1">
            <LocationList
              locations={sorted}
              selectedId={selectedId}
              onSelect={(id) => setSelectedId(id)}
              autoScrollToSelected
              emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
            />
          </div>
        </aside>

        {/* Rechter kolom: kaart */}
        <main className="relative lg:h-auto h-[60vh]">
          <MapView
            locations={sorted}
            selectedId={selectedId}
            onSelect={(id) => setSelectedId(id)}
            bottomSheetHeight={0}
          />
        </main>
      </div>
    );
  }

  // Mobile layout: full-screen map with bottom sheet
  return (
    <div className="relative w-full h-[calc(100dvh-56px)]">
      {/* Full-screen map */}
      <MapView
        locations={sorted}
        selectedId={selectedId}
        onSelect={handleLocationSelect}
        onMapClick={handleMapClick}
        bottomSheetHeight={bottomSheetHeight}
      />

      {/* Bottom sheet overlay */}
      <BottomSheet
        open={isSheetOpen}
        snapPoint={sheetSnapPoint}
        onSnapPointChange={setSheetSnapPoint}
        onClose={() => setIsSheetOpen(false)}
      >
        {selectedId !== -1 && selected ? (
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
                minRating={filters.minRating}
                onlyTurkish={filters.onlyTurkish}
                loading={loading}
                onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
              />
            </div>

            {usingCache && (
              <div className="px-3 py-2 text-xs text-muted-foreground">
                Showing cached data; retrying in background…
              </div>
            )}
            <div className="p-3 border-b">
              <SortBar sort={sort} onChange={(key) => setSort(key)} total={sorted.length} />
            </div>

            <div className="overflow-auto flex-1">
              <LocationList
                locations={sorted}
                selectedId={selectedId}
                onSelect={handleLocationSelect}
                autoScrollToSelected
                emptyText={loading ? "Warming up the backend… Getting your data…" : error ?? "Geen resultaten"}
              />
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  );
}

export default HomePage;
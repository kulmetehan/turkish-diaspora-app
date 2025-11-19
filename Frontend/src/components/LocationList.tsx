import { useEffect, useMemo, useRef } from "react";

import type { LocationMarker } from "@/api/fetchLocations";
import { cn } from "@/lib/ui/cn";

type Props = {
  locations: LocationMarker[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
  onSelectDetail?: (id: string) => void;
  onShowOnMap?: (id: string) => void;
  autoScrollToSelected?: boolean;
  emptyText?: string; // Keep for backward compatibility, but may not be used
  fullHeight?: boolean;
  isLoading?: boolean; // NEW: global loading state
  error?: string | null; // NEW: global error state
  hasActiveSearch?: boolean; // NEW: whether there's an active search/filter
};

export default function LocationList({
  locations,
  selectedId,
  onSelect,
  onSelectDetail,
  onShowOnMap,
  autoScrollToSelected = true,
  emptyText = "Geen resultaten",
  fullHeight = false,
  isLoading = false,
  error = null,
  hasActiveSearch = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Zorg dat onze refs altijd up-to-date zijn met de zichtbare lijst
  const ids = useMemo(() => locations.map((l) => l.id).join(","), [locations]);

  useEffect(() => {
    // Cleanup refs van items die niet meer bestaan
    const keep = new Set(locations.map((l) => l.id));
    for (const id of Array.from(itemRefs.current.keys())) {
      if (!keep.has(id)) itemRefs.current.delete(id);
    }
  }, [ids, locations]);

  // Auto-scroll naar geselecteerd item
  useEffect(() => {
    if (!autoScrollToSelected || !selectedId) return;
    const el = itemRefs.current.get(selectedId);
    const container = containerRef.current;
    if (!el || !container) return;

    const box = el.getBoundingClientRect();
    const cbox = container.getBoundingClientRect();
    const outside = box.top < cbox.top || box.bottom > cbox.bottom;

    if (outside) {
      el.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [selectedId, autoScrollToSelected]);

  // Loading state
  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 text-center text-muted-foreground">
        Warming up the backend… Getting your data…
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-xl border bg-card p-6 text-center text-muted-foreground">
        {error || "Er ging iets mis bij het laden van de locaties."}
      </div>
    );
  }

  // Empty state - distinguish between search vs no data
  if (!locations.length) {
    const message = hasActiveSearch
      ? "Geen resultaten gevonden voor deze zoekopdracht."
      : "Er zijn nog geen locaties beschikbaar in deze stad.";
    return (
      <div className="rounded-xl border bg-card p-6 text-center text-muted-foreground">
        {message}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "rounded-xl border bg-card divide-y overflow-auto",
        fullHeight ? "h-full max-h-none" : "max-h-[calc(100vh-220px)]",
      )}
    >
      {locations.map((l) => {
        const active = l.id === selectedId;
        return (
          <div
            key={l.id}
            ref={(el) => {
              // callback-ref mag niets teruggeven:
              if (el) itemRefs.current.set(l.id, el);
              else itemRefs.current.delete(l.id);
            }}
            role="button"
            className={cn(
              "px-4 py-3 cursor-pointer transition-all duration-150 ease-out",
              "hover:bg-accent/40 hover:shadow-sm",
              active ? "bg-accent/60 border-l-4 border-brand-red shadow-md" : ""
            )}
            onClick={() => onSelect?.(l.id)}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium">{l.name}</div>
              <div className="flex items-center gap-2">
                {onShowOnMap && (
                  <button
                    type="button"
                    className="text-xs text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    onClick={(e) => {
                      e.stopPropagation();
                      onShowOnMap(l.id);
                    }}
                  >
                    Toon op kaart
                  </button>
                )}
                {onSelectDetail && (
                  <button
                    type="button"
                    className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectDetail(l.id);
                    }}
                  >
                    Details
                  </button>
                )}
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              {l.category_label ?? l.category ?? "—"} • {l.is_turkish ? "Turks" : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

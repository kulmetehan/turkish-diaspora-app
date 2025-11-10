import type { LocationMarker } from "@/api/fetchLocations";
import { useEffect, useMemo, useRef } from "react";

type Props = {
  locations: LocationMarker[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
  onSelectDetail?: (id: string) => void;
  onShowOnMap?: (id: string) => void;
  autoScrollToSelected?: boolean;
  emptyText?: string;
};

export default function LocationList({
  locations,
  selectedId,
  onSelect,
  onSelectDetail,
  onShowOnMap,
  autoScrollToSelected = true,
  emptyText = "Geen resultaten",
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

  if (!locations.length) {
    return (
      <div className="rounded-xl border bg-card p-6 text-center text-muted-foreground">
        {emptyText}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="rounded-xl border bg-card divide-y max-h-[calc(100vh-220px)] overflow-auto"
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
            className={`px-4 py-3 cursor-pointer hover:bg-accent/40 transition-colors ${active ? "bg-accent/60" : ""}`}
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

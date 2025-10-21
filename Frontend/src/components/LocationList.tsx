import { useEffect, useMemo, useRef } from "react";
import type { Location } from "@/lib/api/location";

type Props = {
  locations: Location[];
  selectedId: number | null;
  onSelect?: (id: number) => void;
  autoScrollToSelected?: boolean;
  emptyText?: string;
};

export default function LocationList({
  locations,
  selectedId,
  onSelect,
  autoScrollToSelected = true,
  emptyText = "Geen resultaten",
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Zorg dat onze refs altijd up-to-date zijn met de zichtbare lijst
  const ids = useMemo(() => locations.map((l) => l.id).join(","), [locations]);

  useEffect(() => {
    // Cleanup refs van items die niet meer bestaan
    const keep = new Set(locations.map((l) => l.id));
    for (const id of itemRefs.current.keys()) {
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
            className={`px-4 py-3 cursor-pointer hover:bg-accent/40 ${active ? "bg-accent/60" : ""}`}
            onClick={() => onSelect?.(l.id)}
          >
            <div className="flex items-center justify-between">
              <div className="font-medium">{l.name}</div>
              {typeof l.rating === "number" ? (
                <div className="text-xs px-2 py-0.5 rounded bg-emerald-600/10 text-emerald-700 border border-emerald-600/20">
                  ★ {l.rating.toFixed(1)}
                </div>
              ) : null}
            </div>
            <div className="text-xs text-muted-foreground">
              {l.category ?? "—"} • {l.is_turkish ? "Turks" : "—"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

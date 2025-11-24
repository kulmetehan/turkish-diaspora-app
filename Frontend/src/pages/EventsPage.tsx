import { useCallback, useEffect, useMemo, useState } from "react";

import type { EventItem } from "@/api/events";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EventDetailOverlay } from "@/components/events/EventDetailOverlay";
import { EventList } from "@/components/events/EventList";
import { EventMapView } from "@/components/events/EventMapView";
import { eventHasCoordinates } from "@/components/events/eventFormatters";
import { useEventsFeed } from "@/hooks/useEventsFeed";

export default function EventsPage() {
  const {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    loadMore,
    reload,
  } = useEventsFeed({ pageSize: 20 });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "map">("list");

  const detailEvent = useMemo(
    () => items.find((event) => event.id === detailId) ?? null,
    [items, detailId],
  );

  useEffect(() => {
    if (selectedId === null) return;
    if (!items.some((event) => event.id === selectedId)) {
      setSelectedId(null);
    }
  }, [items, selectedId]);

  useEffect(() => {
    if (detailId === null) return;
    if (!items.some((event) => event.id === detailId)) {
      setDetailId(null);
    }
  }, [items, detailId]);

  const handleSelect = useCallback((id: number | null) => {
    setSelectedId(id);
  }, []);

  const handleOpenDetail = useCallback((id: number) => {
    setSelectedId(id);
    setDetailId(id);
  }, []);

  const handleShowOnMap = useCallback(
    (event: EventItem) => {
      if (!eventHasCoordinates(event)) {
        return;
      }
      setSelectedId(event.id);
      setViewMode("map");
    },
    [],
  );

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 rounded-[32px] border border-border bg-card px-5 py-5 text-foreground shadow-card sm:py-8">
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-red">
          Turkspot Highlights
        </p>
        <h1 className="text-3xl font-semibold text-foreground">Events & bijeenkomsten</h1>
        <p className="text-sm text-muted-foreground">
          Ontdek culturele activiteiten, community meetups en zakelijke bijeenkomsten binnen de Turkse diaspora in Nederland.
        </p>
      </header>

      <div className="rounded-2xl border border-border bg-card p-3 shadow-soft">
        <Tabs
          value={viewMode}
          onValueChange={(value) => {
            if (value === "map" || value === "list") {
              setViewMode(value);
            }
          }}
        >
          <TabsList className="grid w-full grid-cols-2 rounded-xl border border-border bg-surface-muted p-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            <TabsTrigger value="list" data-view="list" className="flex items-center justify-center gap-2 rounded-lg py-2 text-sm text-foreground data-[state=active]:bg-[hsl(var(--brand-red-strong))] data-[state=active]:text-brand-white">
              Lijst
            </TabsTrigger>
            <TabsTrigger value="map" data-view="map" className="flex items-center justify-center gap-2 rounded-lg py-2 text-sm text-foreground data-[state=active]:bg-[hsl(var(--brand-red-strong))] data-[state=active]:text-brand-white">
              Kaart
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {viewMode === "list" ? (
        <EventList
          events={items}
          selectedId={selectedId}
          onSelect={handleSelect}
          onSelectDetail={handleOpenDetail}
          onShowOnMap={handleShowOnMap}
          isLoading={isLoading}
          isLoadingMore={isLoadingMore}
          error={error}
          hasMore={hasMore}
          onLoadMore={loadMore}
          onRetry={reload}
        />
      ) : (
        <EventMapView
          events={items}
          selectedId={selectedId}
          detailId={detailId}
          onSelect={handleSelect}
          onOpenDetail={handleOpenDetail}
        />
      )}

      <EventDetailOverlay
        event={detailEvent}
        open={Boolean(detailEvent)}
        onClose={() => setDetailId(null)}
      />
    </div>
  );
}


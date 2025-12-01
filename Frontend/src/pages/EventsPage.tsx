import { useCallback, useEffect, useMemo } from "react";

import type { EventItem } from "@/api/events";
import { AppViewportShell, PageShell } from "@/components/layout";
import { EventDetailOverlay } from "@/components/events/EventDetailOverlay";
import { EventList } from "@/components/events/EventList";
import { EventMapView } from "@/components/events/EventMapView";
import { eventHasCoordinates } from "@/components/events/eventFormatters";
import { surfaceTabsList, surfaceTabsTrigger } from "@/components/ui/tabStyles";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useEventsFeed } from "@/hooks/useEventsFeed";
import { cn } from "@/lib/ui/cn";
import { navigationActions, useEventsNavigation } from "@/state/navigation";

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

  // Use navigation store for events state
  const eventsNavigation = useEventsNavigation();
  const selectedId = eventsNavigation.selectedId;
  const detailId = eventsNavigation.detailId;
  const viewMode = eventsNavigation.viewMode;

  const detailEvent = useMemo(
    () => items.find((event) => event.id === detailId) ?? null,
    [items, detailId],
  );

  useEffect(() => {
    if (selectedId === null) return;
    if (!items.some((event) => event.id === selectedId)) {
      navigationActions.setEvents({ selectedId: null });
    }
  }, [items, selectedId]);

  useEffect(() => {
    if (detailId === null) return;
    if (!items.some((event) => event.id === detailId)) {
      navigationActions.setEvents({ detailId: null });
    }
  }, [items, detailId]);

  const handleSelect = useCallback((id: number | null) => {
    navigationActions.setEvents({ selectedId: id });
  }, []);

  const handleOpenDetail = useCallback((id: number) => {
    navigationActions.setEvents({ selectedId: id, detailId: id });
  }, []);

  const handleShowOnMap = useCallback(
    (event: EventItem) => {
      if (!eventHasCoordinates(event)) {
        return;
      }
      navigationActions.setEvents({ selectedId: event.id, viewMode: "map" });
    },
    [],
  );

  const handleViewModeChange = useCallback((mode: "list" | "map") => {
    navigationActions.setEvents({ viewMode: mode });
  }, []);

  const handleCloseDetail = useCallback(() => {
    navigationActions.setEvents({ detailId: null });
  }, []);

  const handleScrollPositionChange = useCallback((scrollTop: number) => {
    navigationActions.setEvents({ scrollTop });
  }, []);

  return (
    <AppViewportShell variant="content">
      <PageShell
        title="Events & bijeenkomsten"
        subtitle="Ontdek culturele activiteiten, community meetups en zakelijke bijeenkomsten binnen de Turkse diaspora in Nederland."
        maxWidth="5xl"
      >
        <div className="rounded-3xl border border-border bg-card p-4 shadow-soft">
          <Tabs
          value={viewMode}
          onValueChange={(value) => {
            if (value === "map" || value === "list") {
              handleViewModeChange(value);
            }
          }}
        >
          <TabsList className={cn(surfaceTabsList, "grid w-full grid-cols-2 bg-card")}>
            <TabsTrigger
              value="list"
              data-view="list"
              className={cn(surfaceTabsTrigger, "flex items-center justify-center gap-2")}
            >
              Lijst
            </TabsTrigger>
            <TabsTrigger
              value="map"
              data-view="map"
              className={cn(surfaceTabsTrigger, "flex items-center justify-center gap-2")}
            >
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
          scrollTop={eventsNavigation.scrollTop}
          onScrollPositionChange={handleScrollPositionChange}
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
          onClose={handleCloseDetail}
        />
      </PageShell>
    </AppViewportShell>
  );
}


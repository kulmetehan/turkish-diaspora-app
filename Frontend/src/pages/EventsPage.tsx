import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { EventItem } from "@/api/events";
import { FooterTabs } from "@/components/FooterTabs";
import { EventCategoryFilterBar } from "@/components/events/EventCategoryFilterBar";
import { EventDateRangePicker } from "@/components/events/EventDateRangePicker";
import { EventDetailOverlay } from "@/components/events/EventDetailOverlay";
import { EventList } from "@/components/events/EventList";
import { EventMapView } from "@/components/events/EventMapView";
import { EventMonthFilterBar } from "@/components/events/EventMonthFilterBar";
import { EventsIntroHeading } from "@/components/events/EventsIntroHeading";
import { eventHasCoordinates } from "@/components/events/eventFormatters";
import { AppHeader } from "@/components/feed/AppHeader";
import { AppViewportShell } from "@/components/layout";
import { useEventsFeed } from "@/hooks/useEventsFeed";
import { SeoHead } from "@/lib/seo/SeoHead";
import { useSeo } from "@/lib/seo/useSeo";
import {
  readEventCategoriesFromHash,
  subscribeToEventCategoriesHashChange,
  writeEventCategoriesToHash,
  type EventCategoryKey,
} from "@/lib/routing/eventCategories";
import { navigationActions, useEventsNavigation } from "@/state/navigation";

function categoriesAreEqual(a: EventCategoryKey[], b: EventCategoryKey[]) {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

export default function EventsPage() {
  const seo = useSeo();
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);

  // Use navigation store for events state
  const eventsNavigation = useEventsNavigation();
  
  // Read hash params (for shareable URLs) - these take priority
  const hashCategories = readEventCategoriesFromHash();
  const hasHashCategories = hashCategories.length > 0;

  // Priority: hash params (if present) > store values
  // Initialize state: if hash has values, use them (and sync to store), otherwise use store
  const [selectedCategories, setSelectedCategories] = useState<EventCategoryKey[]>(() => {
    if (hasHashCategories) {
      // Sync hash values to store
      navigationActions.setEvents({ categories: hashCategories });
      return hashCategories;
    }
    return eventsNavigation.categories;
  });

  const {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    loadMore,
    reload,
  } = useEventsFeed({ 
    pageSize: 20, 
    dateFrom, 
    dateTo,
    categories: selectedCategories.length > 0 ? selectedCategories : undefined,
  });

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

  // Handle hash change listener (like NewsPage)
  useEffect(() => {
    const handleHashChange = () => {
      const nextCategories = readEventCategoriesFromHash();
      setSelectedCategories((current) => {
        if (!categoriesAreEqual(current, nextCategories)) {
          return nextCategories;
        }
        return current;
      });
    };
    return subscribeToEventCategoriesHashChange(handleHashChange);
  }, []);

  // Sync categories to hash and store
  useEffect(() => {
    writeEventCategoriesToHash(selectedCategories);
    // Also update store
    navigationActions.setEvents({ categories: selectedCategories });
  }, [selectedCategories]);

  const handleCategoriesChange = useCallback((next: EventCategoryKey[]) => {
    setSelectedCategories((current) => (categoriesAreEqual(current, next) ? current : next));
  }, []);

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

  // Handle month selection - set date range to first and last day of month
  const handleMonthSelect = useCallback((month: number | null) => {
    setSelectedMonth(month);
    if (month === null) {
      setDateFrom(null);
      setDateTo(null);
    } else {
      const currentYear = new Date().getFullYear();
      const firstDay = new Date(currentYear, month - 1, 1);
      const lastDay = new Date(currentYear, month, 0); // Last day of the month

      // Format as YYYY-MM-DD
      const formatDate = (date: Date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
      };

      setDateFrom(formatDate(firstDay));
      setDateTo(formatDate(lastDay));
    }
  }, []);

  const handleCloseDetail = useCallback(() => {
    navigationActions.setEvents({ detailId: null });
  }, []);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const scrollRestoredRef = useRef(false);
  const scrollThrottleRef = useRef<number | null>(null);

  const handleScrollPositionChange = useCallback((scrollTop: number) => {
    navigationActions.setEvents({ scrollTop });
  }, []);

  const handleNotificationClick = useCallback(() => {
    // TODO: Implement notification navigation
    console.log("Notification clicked");
  }, []);

  // Restore scroll position on mount
  useEffect(() => {
    if (scrollRestoredRef.current || !scrollContainerRef.current || isLoading || items.length === 0) {
      return;
    }

    const scrollTop = eventsNavigation.scrollTop;
    if (scrollTop > 0) {
      requestAnimationFrame(() => {
        if (scrollContainerRef.current && !scrollRestoredRef.current) {
          scrollContainerRef.current.scrollTo({ top: scrollTop, behavior: "auto" });
          scrollRestoredRef.current = true;
        }
      });
    } else {
      scrollRestoredRef.current = true;
    }
  }, [eventsNavigation.scrollTop, isLoading, items.length]);

  // Track scroll position changes
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !handleScrollPositionChange) return;

    const handleScroll = () => {
      if (scrollThrottleRef.current !== null) {
        window.cancelAnimationFrame(scrollThrottleRef.current);
      }

      scrollThrottleRef.current = window.requestAnimationFrame(() => {
        if (container) {
          handleScrollPositionChange(container.scrollTop);
        }
      });
    };

    container.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      container.removeEventListener("scroll", handleScroll);
      if (scrollThrottleRef.current !== null) {
        window.cancelAnimationFrame(scrollThrottleRef.current);
        scrollThrottleRef.current = null;
      }
    };
  }, [handleScrollPositionChange]);

  return (
    <>
      <SeoHead {...seo} />
      <AppViewportShell variant="content">
        <div className="flex flex-col h-full relative">
        {/* Red gradient overlay */}
        <div
          className="absolute inset-x-0 top-0 pointer-events-none z-0"
          style={{
            height: '25%',
            background: 'linear-gradient(180deg, hsl(var(--brand-red) / 0.10) 0%, hsl(var(--brand-red) / 0.03) 50%, transparent 100%)',
          }}
        />
        <AppHeader
          onNotificationClick={handleNotificationClick}
        />
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto px-4 pb-24 relative z-10"
        >
          <EventsIntroHeading
            viewMode={viewMode}
            onViewModeChange={handleViewModeChange}
          />
          <EventDateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateFromChange={(date) => {
              setDateFrom(date);
              // Clear month selection when manually changing dates
              setSelectedMonth(null);
            }}
            onDateToChange={(date) => {
              setDateTo(date);
              // Clear month selection when manually changing dates
              setSelectedMonth(null);
            }}
            onClear={() => {
              setSelectedMonth(null);
            }}
          />
          <EventMonthFilterBar
            selectedMonth={selectedMonth}
            onMonthSelect={handleMonthSelect}
            className="mt-1"
          />
          <EventCategoryFilterBar
            selected={selectedCategories}
            onChange={handleCategoriesChange}
            className="mt-1"
          />

          {detailId && detailEvent ? (
            <EventDetailOverlay
              event={detailEvent}
              onBackToList={handleCloseDetail}
            />
          ) : viewMode === "list" ? (
            <div className="mt-2">
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
            </div>
          ) : (
            <div className="mt-2">
              <EventMapView
                events={items}
                selectedId={selectedId}
                detailId={detailId}
                onSelect={handleSelect}
                onOpenDetail={handleOpenDetail}
              />
            </div>
          )}
        </div>
        <FooterTabs />
      </div>
    </AppViewportShell>
    </>
  );
}


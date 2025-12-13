import { useMemo } from "react";

import type { EventItem } from "@/api/events";
import type { LocationMarker } from "@/api/fetchLocations";
import MapView from "@/components/MapView";
import { Card } from "@/components/ui/card";
import { ViewportProvider } from "@/contexts/viewport";
import { eventHasCoordinates, formatCategoryLabel } from "./eventFormatters";

type EventMapViewProps = {
  events: EventItem[];
  selectedId: number | null;
  detailId: number | null;
  onSelect?: (id: number | null) => void;
  onOpenDetail?: (id: number) => void;
};

function eventToLocationMarker(event: EventItem): LocationMarker {
  return {
    id: String(event.id),
    name: event.title,
    lat: event.lat ?? null,
    lng: event.lng ?? null,
    address: event.location_text ?? null,
    city: event.city_key ?? undefined,
    category: event.category_key ?? "event",
    category_key: event.category_key ?? undefined,
    category_label: formatCategoryLabel(event.category_key),
    state: "PUBLISHED",
    rating: null,
    confidence_score: null,
    is_turkish: false,
  };
}

export function EventMapView({
  events,
  selectedId,
  detailId,
  onSelect,
  onOpenDetail,
}: EventMapViewProps) {
  const markers = useMemo(() => {
    // Debug: log ALL events first to see what we receive
    if (process.env.NODE_ENV === 'development') {
      console.log('[EventMapView] ===== DEBUG START =====');
      console.log('[EventMapView] Total events received:', events.length);
      events.forEach((event, idx) => {
        const hasCoords = eventHasCoordinates(event);
        console.log(`[EventMapView] Event ${idx + 1}/${events.length}: ID=${event.id}, Title="${event.title}"`);
        console.log(`  - lat: ${event.lat} (type: ${typeof event.lat}, null?: ${event.lat === null}, undefined?: ${event.lat === undefined})`);
        console.log(`  - lng: ${event.lng} (type: ${typeof event.lng}, null?: ${event.lng === null}, undefined?: ${event.lng === undefined})`);
        console.log(`  - eventHasCoordinates(): ${hasCoords}`);
        if (event.lat != null || event.lng != null) {
          console.log(`  - Raw values: lat=${JSON.stringify(event.lat)}, lng=${JSON.stringify(event.lng)}`);
        }
      });
    }

    // Filter events with coordinates
    const eventsWithCoords = events.filter(eventHasCoordinates);
    if (process.env.NODE_ENV === 'development') {
      console.log('[EventMapView] Events with coordinates:', eventsWithCoords.length, 'out of', events.length);
      if (eventsWithCoords.length > 0) {
        eventsWithCoords.forEach(event => {
          console.log(`[EventMapView] ✓ Event ${event.id} (${event.title}): lat=${event.lat}, lng=${event.lng}`);
        });
      }
    }

    // Convert to LocationMarker format
    const markers = eventsWithCoords.map(eventToLocationMarker);

    if (process.env.NODE_ENV === 'development') {
      console.log('[EventMapView] Converted markers:', markers.length);
      markers.forEach(marker => {
        console.log(`[EventMapView] Marker ID=${marker.id}, name="${marker.name}", lat=${marker.lat} (${typeof marker.lat}), lng=${marker.lng} (${typeof marker.lng})`);
        if (typeof marker.lat !== 'number' || typeof marker.lng !== 'number') {
          console.error(`[EventMapView] ⚠️ INVALID MARKER: lat/lng are not numbers!`, marker);
        }
      });
      console.log('[EventMapView] ===== DEBUG END =====');
    }

    return markers;
  }, [events]);

  if (!markers.length) {
    return (
      <Card className="rounded-3xl border border-border bg-card p-6 text-sm text-muted-foreground shadow-soft">
        Er zijn nog geen events met bekende kaartlocaties. Zodra coordinaten beschikbaar
        zijn tonen we ze hier. {/* Backend dependency note */}
      </Card>
    );
  }

  const highlightedId = selectedId != null ? String(selectedId) : null;
  const detailMarkerId = detailId != null ? String(detailId) : null;

  // Compute center of events for initial map view
  const eventCenter = useMemo(() => {
    if (markers.length === 0) return null;

    // If only one event, center on it
    if (markers.length === 1) {
      const marker = markers[0];
      if (marker.lat != null && marker.lng != null &&
        Number.isFinite(marker.lat) && Number.isFinite(marker.lng)) {
        return {
          lng: marker.lng,
          lat: marker.lat,
          zoom: 14, // Good zoom level for a single event
        };
      }
      return null;
    }

    // Multiple events: compute average center
    let sumLat = 0;
    let sumLng = 0;
    let count = 0;

    for (const marker of markers) {
      if (marker.lat != null && marker.lng != null &&
        Number.isFinite(marker.lat) && Number.isFinite(marker.lng)) {
        sumLat += marker.lat;
        sumLng += marker.lng;
        count++;
      }
    }

    if (count === 0) return null;

    return {
      lng: sumLng / count,
      lat: sumLat / count,
      zoom: 12, // Slightly zoomed out for multiple events
    };
  }, [markers]);

  return (
    <ViewportProvider>
      <div className="relative h-[min(70vh,520px)] w-full overflow-hidden rounded-3xl border border-border bg-card shadow-soft">
        <MapView
          locations={markers}
          globalLocations={markers}
          highlightedId={highlightedId}
          detailId={detailMarkerId}
          initialCenterOverride={eventCenter}
          onHighlight={(id) => {
            if (!onSelect) return;
            if (id == null) {
              onSelect(null);
              return;
            }
            const numericId = Number(id);
            onSelect(Number.isNaN(numericId) ? null : numericId);
          }}
          onOpenDetail={(id) => {
            if (!onOpenDetail) return;
            const numericId = Number(id);
            if (Number.isNaN(numericId)) return;
            onOpenDetail(numericId);
          }}
          onMapClick={() => {
            onSelect?.(null);
          }}
          centerOnSelect
        />
      </div>
    </ViewportProvider>
  );
}

export default EventMapView;





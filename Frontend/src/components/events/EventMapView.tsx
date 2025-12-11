import { useMemo } from "react";

import type { EventItem } from "@/api/events";
import type { LocationMarker } from "@/api/fetchLocations";
import MapView from "@/components/MapView";
import { ViewportProvider } from "@/contexts/viewport";
import { Card } from "@/components/ui/card";
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
  const markers = useMemo(
    () => events.filter(eventHasCoordinates).map(eventToLocationMarker),
    [events],
  );

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

  return (
    <ViewportProvider>
      <div className="relative h-[min(70vh,520px)] w-full overflow-hidden rounded-3xl border border-border bg-card shadow-soft">
        <MapView
          locations={markers}
          globalLocations={markers}
          highlightedId={highlightedId}
          detailId={detailMarkerId}
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





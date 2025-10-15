// Frontend/src/components/LocationList.tsx

import React, { useEffect, useMemo, useRef } from "react";
import type { Location } from "../types/location";
import LocationCard from "./LocationCard";
import {
  useSelectedCategories,
  useSelectedLocationId,
  useSortBy,
  selectLocation,
} from "../state/ui";

/**
 * Pure presentational + light behaviour:
 * - Filteren op categorie (uit globale UI store)
 * - Sorteren op afstand of rating (uit globale UI store)
 * - Sync selectie met UI store (list <-> map)
 *
 * Data (locaties) wordt als prop aangereikt door de parent (App/useLocations).
 */

type Props = {
  locations: Location[];
  className?: string;
  /**
   * Wanneer true zal de lijst automatisch naar het geselecteerde item scrollen
   * als selectedLocationId verandert.
   */
  autoScrollToSelected?: boolean;
  /** Optioneel: “Geen resultaten”-tekst overschrijven */
  emptyText?: string;
};

function sortLocations(
  list: Location[],
  sortBy: "distance" | "rating"
): Location[] {
  if (sortBy === "distance") {
    // undefined afstand => onderaan
    return [...list].sort((a, b) => {
      const da = a.distanceKm ?? Number.POSITIVE_INFINITY;
      const db = b.distanceKm ?? Number.POSITIVE_INFINITY;
      return da - db;
    });
  }
  // rating: undefined/null => onderaan
  return [...list].sort((a, b) => {
    const ra = a.rating ?? -Infinity;
    const rb = b.rating ?? -Infinity;
    // Descending
    return rb - ra;
  });
}

const LocationList: React.FC<Props> = ({
  locations,
  className,
  autoScrollToSelected = true,
  emptyText = "Geen resultaten voor de huidige filters.",
}) => {
  const selectedCategories = useSelectedCategories();
  const selectedLocationId = useSelectedLocationId();
  const sortBy = useSortBy();

  // Filter op categorie (één of meerdere). Lege set => geen filter.
  const filtered = useMemo(() => {
    if (!selectedCategories.length) return locations;
    const set = new Set(selectedCategories);
    return locations.filter((l) => (l.category ? set.has(l.category) : false));
  }, [locations, selectedCategories]);

  // Sorteren
  const sorted = useMemo(() => sortLocations(filtered, sortBy), [filtered, sortBy]);

  // Refs voor auto-scroll naar geselecteerde card
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!autoScrollToSelected || !selectedLocationId) return;
    const el = itemRefs.current[selectedLocationId];
    if (el) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedLocationId, autoScrollToSelected]);

  if (!sorted.length) {
    return <div className={className ?? ""}>{emptyText}</div>;
  }

  return (
    <div className={["location-list", className ?? ""].join(" ").trim()} role="list">
      {sorted.map((loc) => {
        const isSelected = loc.id === selectedLocationId;

        return (
          <div
            key={loc.id}
            ref={(el) => {
              itemRefs.current[loc.id] = el;
            }}
            role="listitem"
          >
            <LocationCard
              location={loc}
              isSelected={isSelected}
              onSelect={(id) => selectLocation(id)}
            />
          </div>
        );
      })}
    </div>
  );
};

export default LocationList;

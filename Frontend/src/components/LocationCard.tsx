// Frontend/src/components/LocationCard.tsx

import type { LocationMarker } from "@/api/fetchLocations";
import React from "react";

type Props = {
  location: LocationMarker;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
};

function formatDistance(km?: number): string {
  if (km == null || Number.isNaN(km)) return "—";
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(km < 10 ? 1 : 0)} km`;
}

function getStatusBadge(loc: LocationMarker): { text: string; className: string } {
  // Probeer iets zinvols te tonen met de velden die we hebben.
  // We ondersteunen generieke "state" waarden; zo blijft het future-proof.
  // Op basis van state (val rustig terug op 'Onbekend').
  const s = (loc.state ?? "").toUpperCase();
  if (s.includes("VERIFIED")) return { text: "Geverifieerd", className: "badge badge--success" };
  if (s.includes("CANDIDATE")) return { text: "Kandidaat", className: "badge badge--warn" };
  if (s.includes("REJECT")) return { text: "Afgewezen", className: "badge badge--error" };

  return { text: "Onbekend", className: "badge" };
}

const LocationCard: React.FC<Props> = ({ location, isSelected = false, onSelect }) => {
  const { text: statusText, className: badgeClass } = getStatusBadge(location);

  const handleClick = () => {
    if (onSelect && location.id) onSelect(location.id);
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-selected={isSelected}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={[
        "loc-card",
        isSelected ? "loc-card--selected" : "",
      ].join(" ").trim()}
    >
      <div className="loc-card__header">
        <h3 className="loc-card__title">{location.name}</h3>
        <span className={badgeClass}>{statusText}</span>
      </div>

      <div className="loc-card__meta">
        <div className="loc-card__row">
          <span className="loc-card__label">Categorie</span>
          <span className="loc-card__value">{location.category_label ?? location.category ?? "—"}</span>
        </div>
      </div>
    </div>
  );
};

export default LocationCard;

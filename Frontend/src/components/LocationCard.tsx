// Frontend/src/components/LocationCard.tsx

import React from "react";
import type { Location } from "../types/location";

type Props = {
  location: Location;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
};

function formatDistance(km?: number): string {
  if (km == null || Number.isNaN(km)) return "—";
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(km < 10 ? 1 : 0)} km`;
}

function formatRating(r?: number | null, total?: number | null): string {
  if (r == null || Number.isNaN(r)) return "—";
  const count = total ?? 0;
  return `${r.toFixed(1)} ★${count ? ` (${count})` : ""}`;
}

function getStatusBadge(loc: Location): { text: string; className: string } {
  // Probeer iets zinvols te tonen met de velden die we hebben.
  // We ondersteunen generieke "state" waarden; zo blijft het future-proof.
  const now = Date.now();

  // Recent geverifieerd? (7 dagen)
  if (loc.last_verified_at) {
    const ms = now - new Date(loc.last_verified_at).getTime();
    const days = ms / (1000 * 60 * 60 * 24);
    if (!Number.isNaN(days) && days <= 7) {
      return { text: "Nieuw", className: "badge badge--success" };
    }
  }

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
          <span className="loc-card__label">Adres</span>
          <span className="loc-card__value">{location.address ?? "—"}</span>
        </div>
        <div className="loc-card__row">
          <span className="loc-card__label">Categorie</span>
          <span className="loc-card__value">{location.category ?? "—"}</span>
        </div>
        <div className="loc-card__row">
          <span className="loc-card__label">Beoordeling</span>
          <span className="loc-card__value">
            {formatRating(location.rating ?? null, location.user_ratings_total ?? null)}
          </span>
        </div>
        <div className="loc-card__row">
          <span className="loc-card__label">Afstand</span>
          <span className="loc-card__value">{formatDistance(location.distanceKm)}</span>
        </div>
      </div>
    </div>
  );
};

export default LocationCard;

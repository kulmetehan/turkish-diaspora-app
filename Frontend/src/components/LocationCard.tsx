// Frontend/src/components/LocationCard.tsx

import type { LocationMarker } from "@/api/fetchLocations";
import React from "react";
import { cn } from "@/lib/ui/cn";

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
      className={cn(
        "border rounded-xl p-3.5 my-2 cursor-pointer bg-card text-card-foreground transition-colors",
        "hover:bg-accent/40 hover:shadow-sm",
        isSelected && "bg-accent/60 border-brand-red shadow-md"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-base leading-tight m-0 font-semibold">{location.name}</h3>
        <span className={badgeClass}>{statusText}</span>
      </div>

      <div className="mt-2 grid gap-1">
        <div className="grid grid-cols-[110px_1fr] gap-2">
          <span className="text-xs text-muted-foreground">Categorie</span>
          <span className="text-sm">{location.category_label ?? location.category ?? "—"}</span>
        </div>
      </div>
    </div>
  );
};

export default LocationCard;

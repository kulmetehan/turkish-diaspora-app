// Frontend/src/components/LocationCard.tsx

import type { LocationMarker } from "@/api/fetchLocations";
import React from "react";
import { cn } from "@/lib/ui/cn";

type Props = {
  location: LocationMarker;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
};

function getStatusBadge(loc: LocationMarker): { text: string; className: string } {
  const s = (loc.state ?? "").toUpperCase();
  if (s.includes("VERIFIED")) {
    return {
      text: "Geverifieerd",
      className:
        "inline-flex items-center rounded-full border border-emerald-400/50 bg-emerald-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-emerald-100",
    };
  }
  if (s.includes("CANDIDATE")) {
    return {
      text: "Kandidaat",
      className:
        "inline-flex items-center rounded-full border border-amber-400/50 bg-amber-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-amber-50",
    };
  }
  if (s.includes("REJECT")) {
    return {
      text: "Afgewezen",
      className:
        "inline-flex items-center rounded-full border border-rose-500/50 bg-rose-500/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-rose-100",
    };
  }

  return {
    text: "Onbekend",
    className:
      "inline-flex items-center rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-brand-white/70",
  };
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
        "my-2 cursor-pointer rounded-3xl border border-white/10 bg-surface-raised/75 p-4 text-foreground shadow-soft transition-all duration-200",
        "hover:border-white/25 hover:bg-surface-raised/90 hover:text-brand-white",
        isSelected &&
          "bg-gradient-card text-brand-white shadow-[0_30px_45px_rgba(0,0,0,0.55)] ring-2 ring-brand-white/60",
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

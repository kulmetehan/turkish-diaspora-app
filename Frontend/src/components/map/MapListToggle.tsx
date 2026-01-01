// Frontend/src/components/map/MapListToggle.tsx
// Floating toggle component for switching between Map and List view modes

import { Icon } from "@/components/Icon";
import type { ViewMode } from "@/lib/routing/viewMode";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

type MapListToggleProps = {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
};

export function MapListToggle({ viewMode, onViewModeChange }: MapListToggleProps) {
  const { t } = useTranslation();
  return (
    <div className="inline-flex items-center gap-1 rounded-full bg-white p-1 shadow-card">
      <button
        type="button"
        onClick={() => {
          if (viewMode !== "map") {
            onViewModeChange("map");
          }
        }}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-full px-8 py-2.5 text-sm font-semibold transition-all",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
          viewMode === "map"
            ? "bg-primary text-primary-foreground shadow-soft"
            : "bg-transparent text-gray-900 hover:bg-primary hover:text-primary-foreground"
        )}
        aria-pressed={viewMode === "map"}
        aria-label={t("map.toggle.mapView")}
      >
        <Icon name="Map" className="h-4 w-4" aria-hidden />
        <span>{t("map.toggle.map")}</span>
      </button>
      <button
        type="button"
        onClick={() => {
          if (viewMode !== "list") {
            onViewModeChange("list");
          }
        }}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-full px-8 py-2.5 text-sm font-semibold transition-all",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
          viewMode === "list"
            ? "bg-primary text-primary-foreground shadow-soft dark:text-black"
            : "bg-transparent text-gray-900 hover:bg-primary hover:text-primary-foreground"
        )}
        aria-pressed={viewMode === "list"}
        aria-label={t("map.toggle.listView")}
      >
        <Icon name="List" className="h-4 w-4" aria-hidden />
        <span>{t("map.toggle.list")}</span>
      </button>
    </div>
  );
}









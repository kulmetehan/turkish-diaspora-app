// Frontend/src/components/events/EventsIntroHeading.tsx
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";

export interface EventsIntroHeadingProps {
  className?: string;
  viewMode?: "list" | "map";
  onViewModeChange?: (mode: "list" | "map") => void;
}

export function EventsIntroHeading({
  className,
  viewMode = "list",
  onViewModeChange,
}: EventsIntroHeadingProps) {
  const { t } = useTranslation();
  return (
    <div className={cn("px-4 py-1.5 flex items-center justify-between", className)}>
      <h2 className="text-2xl font-gilroy font-black text-foreground">
        {t("events.heading")}
      </h2>
      {onViewModeChange && (
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => onViewModeChange("list")}
            className={cn(
              "text-xs font-gilroy font-medium transition-colors",
              viewMode === "list"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {t("events.viewMode.list")}
          </button>
          <span className="text-xs text-muted-foreground">|</span>
          <button
            type="button"
            onClick={() => onViewModeChange("map")}
            className={cn(
              "text-xs font-gilroy font-medium transition-colors",
              viewMode === "map"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {t("events.viewMode.map")}
          </button>
        </div>
      )}
    </div>
  );
}

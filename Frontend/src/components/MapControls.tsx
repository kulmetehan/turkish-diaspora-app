import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

type MapControlsProps = {
  onResetNorth: () => void;
  onLocateUser: () => void;
  locating: boolean;
  disabled?: boolean;
};

export default function MapControls({ onResetNorth, onLocateUser, locating, disabled = false }: MapControlsProps) {
  return (
    <div
      data-map-controls
      className={cn(
        "pointer-events-auto fixed right-3 text-brand-white md:right-4",
        "bottom-[var(--bottom-offset)]",
        "z-40 flex flex-col gap-2",
      )}
      style={{ paddingRight: "calc(env(safe-area-inset-right, 0px))" }}
    >
      <Button
        type="button"
        size="icon"
        variant="secondary"
        onClick={onResetNorth}
        disabled={disabled}
        aria-label="Reset bearing to North"
        title="Reset bearing to North"
        className="h-12 w-12 rounded-2xl border border-white/15 bg-surface-raised/80 text-current shadow-soft transition focus-visible:ring-2 focus-visible:ring-brand-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent hover:bg-white/10"
      >
        <Icon name="Compass" sizeRem={1.1} aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="secondary"
        onClick={onLocateUser}
        disabled={disabled || locating}
        aria-label="Show my location"
        title="Show my location"
        className="h-12 w-12 rounded-2xl border border-white/15 bg-surface-raised/80 text-current shadow-soft transition focus-visible:ring-2 focus-visible:ring-brand-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent hover:bg-white/10"
      >
        <Icon
          name="LocateFixed"
          sizeRem={1.1}
          aria-hidden
          className={locating ? "animate-pulse" : undefined}
        />
      </Button>
    </div>
  );
}


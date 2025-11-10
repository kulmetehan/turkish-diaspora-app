import { Button } from "@/components/ui/button";
import { Icon } from "@/components/Icon";

type MapControlsProps = {
  onResetNorth: () => void;
  onLocateUser: () => void;
  locating: boolean;
  disabled?: boolean;
};

export default function MapControls({ onResetNorth, onLocateUser, locating, disabled = false }: MapControlsProps) {
  return (
    <div
      className="pointer-events-none absolute right-4 top-4 z-20 flex flex-col items-end gap-2 pt-4"
      style={{
        paddingTop: "calc(env(safe-area-inset-top, 0px) + 1rem)",
        paddingRight: "calc(env(safe-area-inset-right, 0px))",
      }}
    >
      <div className="pointer-events-auto flex flex-col gap-2">
        <Button
          type="button"
          size="icon"
          variant="secondary"
          onClick={onResetNorth}
          disabled={disabled}
          aria-label="Reset bearing to north"
        >
          <Icon name="Compass" sizeRem={1.1} />
        </Button>
        <Button
          type="button"
          size="icon"
          variant="secondary"
          onClick={onLocateUser}
          disabled={disabled || locating}
          aria-label="Center map on my location"
        >
          <Icon name="LocateFixed" sizeRem={1.1} className={locating ? "animate-pulse" : undefined} />
        </Button>
      </div>
    </div>
  );
}


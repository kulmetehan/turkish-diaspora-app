import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

type AddLocationButtonProps = {
  onClick: () => void;
  disabled?: boolean;
};

export default function AddLocationButton({ onClick, disabled = false }: AddLocationButtonProps) {
  return (
    <Button
      type="button"
      size="icon"
      onClick={onClick}
      disabled={disabled}
      aria-label="Locatie toevoegen"
      title="Locatie toevoegen"
      className={cn(
        "h-12 w-12 rounded-full border-0 bg-[#e63946] text-white shadow-soft transition",
        "focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent",
        "hover:bg-[#c1121f]",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <Icon name="Plus" sizeRem={1.1} className="text-white" aria-hidden />
    </Button>
  );
}










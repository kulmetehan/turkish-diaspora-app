import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

type AddEventButtonProps = {
  onClick: () => void;
  disabled?: boolean;
};

export default function AddEventButton({ onClick, disabled = false }: AddEventButtonProps) {
  return (
    <Button
      type="button"
      size="icon"
      onClick={onClick}
      disabled={disabled}
      aria-label="Event toevoegen"
      title="Event toevoegen"
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


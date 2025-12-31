import { Icon } from "@/components/Icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";

interface CheckInsToggleButtonProps {
  isCheckInsMode: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export default function CheckInsToggleButton({
  isCheckInsMode,
  onToggle,
  disabled = false,
}: CheckInsToggleButtonProps) {
  return (
    <Button
      type="button"
      size="icon"
      onClick={onToggle}
      disabled={disabled}
      aria-label={isCheckInsMode ? "Toon locaties" : "Toon check-ins"}
      title={isCheckInsMode ? "Toon locaties" : "Toon check-ins"}
      className={cn(
        "h-12 w-12 rounded-full border-0 shadow-soft transition",
        "focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent",
        isCheckInsMode
          ? "bg-[#e63946] text-white hover:bg-[#c1121f]"
          : "bg-surface-raised/80 text-foreground hover:bg-surface-muted border border-border",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <Icon
        name={isCheckInsMode ? "ShoppingBag" : "Users"}
        sizeRem={1.1}
        className={isCheckInsMode ? "text-white" : "text-foreground"}
        aria-hidden
      />
    </Button>
  );
}


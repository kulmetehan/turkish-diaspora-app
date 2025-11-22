import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";
import { cn } from "@/lib/ui/cn";

export interface NewsSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  loading?: boolean;
  className?: string;
}

export function NewsSearchBar({
  value,
  onChange,
  onClear,
  loading,
  className,
}: NewsSearchBarProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border/60 bg-background px-3 py-2 shadow-sm",
        "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
        className,
      )}
    >
      <FloatingSearchBar
        value={value}
        onValueChange={onChange}
        onClear={onClear}
        loading={loading}
        ariaLabel="Zoek nieuwsartikelen"
        placeholder="Zoek in diaspora nieuws…"
      />
    </div>
  );
}


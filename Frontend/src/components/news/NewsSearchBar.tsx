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
        "rounded-3xl border border-border bg-surface-raised px-4 py-3 shadow-soft",
        "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
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



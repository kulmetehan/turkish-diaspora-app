import { FloatingSearchBar } from "@/components/search/FloatingSearchBar";

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
    <FloatingSearchBar
      value={value}
      onValueChange={onChange}
      onClear={onClear}
      loading={loading}
      ariaLabel="Zoek nieuwsartikelen"
      placeholder="Zoek in diaspora nieuws…"
      className={className}
    />
  );
}



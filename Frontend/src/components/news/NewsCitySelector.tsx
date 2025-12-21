// Frontend/src/components/news/NewsCitySelector.tsx
import { Button } from "@/components/ui/button";
import type { CityLabelMap } from "@/hooks/useNewsCityPreferences";
import { cn } from "@/lib/ui/cn";

export interface NewsCitySelectorProps {
  cities: string[];
  cityLabels: CityLabelMap;
  onEdit: () => void;
  className?: string;
}

function renderCityList(cities: string[], cityLabels: CityLabelMap) {
  if (!cities.length) {
    return "geen selectie";
  }
  return cities.map((key) => cityLabels[key]?.name ?? key).join(", ");
}

export function NewsCitySelector({
  cities,
  cityLabels,
  onEdit,
  className,
}: NewsCitySelectorProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-3xl border border-border bg-card px-4 py-3 text-xs text-muted-foreground shadow-soft",
        className
      )}
    >
      <span>
        Steden:&nbsp;
        {renderCityList(cities, cityLabels)}
      </span>
      <Button type="button" variant="ghost" size="sm" onClick={onEdit}>
        Wijzig selectie
      </Button>
    </div>
  );
}







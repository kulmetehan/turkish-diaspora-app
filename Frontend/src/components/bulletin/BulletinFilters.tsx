// Frontend/src/components/bulletin/BulletinFilters.tsx
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";
import type { BulletinPostFilters, BulletinCategory } from "@/types/bulletin";

interface BulletinFiltersProps {
  filters: BulletinPostFilters;
  onFiltersChange: (filters: BulletinPostFilters) => void;
  className?: string;
}

const categoryLabels: Record<BulletinCategory, string> = {
  personnel_wanted: "Personeel gezocht",
  offer: "Aanbieding",
  free_for_sale: "Gratis/Te koop",
  event: "Evenement",
  services: "Diensten",
  other: "Overig",
};

const categories: BulletinCategory[] = [
  "personnel_wanted",
  "offer",
  "free_for_sale",
  "event",
  "services",
  "other",
];

export function BulletinFilters({ filters, onFiltersChange, className }: BulletinFiltersProps) {
  const hasActiveFilters =
    filters.category || filters.city || filters.search || (filters.status && filters.status !== "all");

  const handleCategoryToggle = (category: BulletinCategory) => {
    onFiltersChange({
      ...filters,
      category: filters.category === category ? undefined : category,
    });
  };

  const handleClearFilters = () => {
    onFiltersChange({
      status: "all",
      category: undefined,
      city: undefined,
      search: undefined,
    });
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Search */}
      <div className="relative">
        <Icon name="Search" className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Zoek advertenties..."
          value={filters.search || ""}
          onChange={(e) => onFiltersChange({ ...filters, search: e.target.value || undefined })}
          className="pl-9"
        />
      </div>

      {/* Category chips */}
      <div className="flex flex-wrap gap-2">
        {categories.map((category) => (
          <Badge
            key={category}
            variant={filters.category === category ? "default" : "outline"}
            className={cn(
              "cursor-pointer transition-colors",
              filters.category === category && "bg-primary text-primary-foreground"
            )}
            onClick={() => handleCategoryToggle(category)}
          >
            {categoryLabels[category]}
          </Badge>
        ))}
      </div>

      {/* City filter */}
      <Select
        value={filters.city || "all"}
        onValueChange={(value) =>
          onFiltersChange({ ...filters, city: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger>
          <SelectValue placeholder="Selecteer stad" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Alle steden</SelectItem>
          <SelectItem value="Rotterdam">Rotterdam</SelectItem>
          <SelectItem value="Amsterdam">Amsterdam</SelectItem>
          <SelectItem value="Den Haag">Den Haag</SelectItem>
          <SelectItem value="Utrecht">Utrecht</SelectItem>
        </SelectContent>
      </Select>

      {/* Clear filters */}
      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={handleClearFilters} className="w-full">
          <Icon name="X" className="h-4 w-4 mr-2" />
          Filters wissen
        </Button>
      )}
    </div>
  );
}


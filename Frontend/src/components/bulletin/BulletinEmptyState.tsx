// Frontend/src/components/bulletin/BulletinEmptyState.tsx
import { Icon } from "@/components/Icon";
import type { BulletinPostFilters } from "@/types/bulletin";

interface BulletinEmptyStateProps {
  filters: BulletinPostFilters;
}

export function BulletinEmptyState({ filters }: BulletinEmptyStateProps) {
  const hasFilters =
    filters.category || filters.city || filters.search || (filters.status && filters.status !== "all");

  if (hasFilters) {
    return (
      <div className="text-center py-12">
        <Icon name="SearchX" className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Geen advertenties gevonden met deze filters</p>
        <p className="text-sm text-muted-foreground mt-2">
          Probeer andere filters of wis alle filters om alle advertenties te zien
        </p>
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <Icon name="MessageSquare" className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
      <p className="text-muted-foreground font-medium">Nog geen advertenties</p>
      <p className="text-sm text-muted-foreground mt-2">
        Wees de eerste om een advertentie te plaatsen!
      </p>
    </div>
  );
}


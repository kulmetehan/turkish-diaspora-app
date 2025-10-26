import { useMemo } from "react";

type CategoryOption = { key: string; label: string };

type Props = {
  search: string;
  category: string;
  onlyTurkish: boolean;
  loading?: boolean;
  categoryOptions?: CategoryOption[];
  onChange: (patch: Partial<{
    search: string;
    category: string;
    onlyTurkish: boolean;
  }>) => void;
};

// Officiële categorieën (TDA-107)
const KNOWN_CATEGORIES = [
  { key: "restaurant", label: "Restaurant" },
  { key: "bakery", label: "Bakkerij" },
  { key: "supermarket", label: "Supermarkt" },
  { key: "barber", label: "Barber" },
  { key: "mosque", label: "Moskee" },
  { key: "travel_agency", label: "Reisbureau" },
  { key: "butcher", label: "Slager" },
  { key: "fast_food", label: "Fastfood" },
] satisfies CategoryOption[];

function toLabelFromKey(key: string): string {
  // Fallback titlecase for when no label is provided
  const parts = String(key || "")
    .replaceAll("/", " ")
    .replaceAll("_", " ")
    .trim()
    .split(/\s+/);
  return parts.map((p) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join(" ");
}

export default function Filters({
  search,
  category,
  onlyTurkish,
  loading,
  categoryOptions,
  onChange,
}: Props) {


  const categories = useMemo(() => {
    const base = (categoryOptions && categoryOptions.length)
      ? categoryOptions
      : KNOWN_CATEGORIES;

    // Zorg dat de huidige category (als die buiten de lijst valt) toch zichtbaar is.
    if (!category || category === "all") return base;
    if (!base.some((c) => c.key === category)) {
      return [{ key: category, label: toLabelFromKey(category) }, ...base];
    }
    return base;
  }, [category, categoryOptions]);

  return (
    <div className="rounded-xl border bg-card p-3 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <label htmlFor="search-input" className="sr-only">Zoek op naam of categorie</label>
        <input
          id="search-input"
          name="search"
          className="w-full rounded-md border px-3 py-2"
          type="text"
          placeholder="Zoek op naam of categorie…"
          value={search}
          onChange={(e) => onChange({ search: e.target.value })}
        />
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="category-select" className="sr-only">Selecteer categorie</label>
        <select
          id="category-select"
          name="category"
          className="rounded-md border px-3 py-2"
          value={category}
          onChange={(e) => onChange({ category: e.target.value })}
        >
          <option value="all">Alle categorieën</option>
          {categories.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>

        {loading ? (
          <span className="text-xs text-muted-foreground">Laden…</span>
        ) : null}
      </div>
    </div>
  );
}

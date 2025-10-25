import { useMemo } from "react";

type Props = {
  search: string;
  category: string;
  onlyTurkish: boolean;
  loading?: boolean;
  onChange: (patch: Partial<{
    search: string;
    category: string;
    onlyTurkish: boolean;
  }>) => void;
};

// Officiële categorieën (TDA-107)
const KNOWN_CATEGORIES = [
  "restaurant",
  "bakery",
  "supermarket",
  "barber",
  "mosque",
  "travel_agency",
  "butcher",
  "fast_food",
];

export default function Filters({
  search,
  category,
  onlyTurkish,
  loading,
  onChange,
}: Props) {


  const categories = useMemo(() => {
    // Zorg dat de huidige category (als die buiten de lijst valt) toch zichtbaar is.
    if (category === "all") return KNOWN_CATEGORIES;
    return category && !KNOWN_CATEGORIES.includes(category)
      ? [category, ...KNOWN_CATEGORIES]
      : KNOWN_CATEGORIES;
  }, [category]);

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
            <option key={c} value={c}>
              {c.charAt(0).toUpperCase() + c.slice(1)}
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

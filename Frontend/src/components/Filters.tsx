import { useMemo } from "react";

type Props = {
  search: string;
  category: string | null;
  minRating: number | null;
  onlyTurkish: boolean;
  loading?: boolean;
  onChange: (patch: Partial<{
    search: string;
    category: string | null;
    minRating: number | null;
    onlyTurkish: boolean;
  }>) => void;
};

// Eventuele categorieën die je wilt tonen (pas aan op je data)
const KNOWN_CATEGORIES = ["restaurant", "bakery", "market", "cafe", "shop", "other"];

export default function Filters({
  search,
  category,
  minRating,
  onlyTurkish,
  loading,
  onChange,
}: Props) {
  const ratingValue = minRating ?? 0;

  const categories = useMemo(() => {
    // Zorg dat de huidige category (als die buiten de lijst valt) toch zichtbaar is.
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
          value={category ?? ""}
          onChange={(e) => onChange({ category: e.target.value || null })}
        >
          <option value="">Alle categorieën</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c.charAt(0).toUpperCase() + c.slice(1)}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <label htmlFor="rating-range" className="text-sm whitespace-nowrap">Min. rating</label>
          <input
            id="rating-range"
            name="minRating"
            className="w-40"
            type="range"
            min={0}
            max={5}
            step={0.5}
            value={ratingValue}
            onChange={(e) => onChange({ minRating: Number(e.target.value) || 0 })}
          />
          <span className="w-8 text-center text-sm">{ratingValue.toFixed(1)}</span>
        </div>

        {loading ? (
          <span className="text-xs text-muted-foreground">Laden…</span>
        ) : null}
      </div>
    </div>
  );
}

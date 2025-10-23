type SortKey = "relevance" | "rating_desc" | "name_asc";

type Props = {
  sort: SortKey;
  total: number;
  onChange: (key: SortKey) => void;
};

export default function SortBar({ sort, total, onChange }: Props) {
  return (
    <div className="rounded-xl border bg-card px-3 py-2 flex items-center justify-between">
      <div className="text-sm text-muted-foreground">
        {total} resultaat{total === 1 ? "" : "en"}
      </div>
      <div className="flex items-center gap-2">
        <label htmlFor="sort-select" className="text-sm">Sorteer op</label>
        <select
          id="sort-select"
          name="sort"
          className="rounded-md border px-3 py-1.5"
          value={sort}
          onChange={(e) => onChange(e.target.value as SortKey)}
        >
          <option value="relevance">Relevantie</option>
          <option value="rating_desc">Rating (hoog → laag)</option>
          <option value="name_asc">Naam (A → Z)</option>
        </select>
      </div>
    </div>
  );
}

// Frontend/src/components/Filters.tsx

import React from "react";
import {
  useSelectedCategories,
  toggleCategory,
  clearCategories,
  setCategories,
} from "../state/ui";

/**
 * Multi-select categorie filter.
 * - Verwacht de lijst met beschikbare categorieën als prop (unik, gesorteerd).
 * - Neemt en schrijft de selectie naar de centrale UI-store.
 */

type Props = {
  categories: string[];
  className?: string;
  title?: string;
  /** Toon een "Alles wissen" knop (default: true) */
  showClear?: boolean;
};

const Filters: React.FC<Props> = ({
  categories,
  className,
  title = "Categorieën",
  showClear = true,
}) => {
  const selected = useSelectedCategories();
  const selectedSet = new Set(selected);

  const onToggle = (cat: string) => {
    toggleCategory(cat);
  };

  const onClear = () => {
    clearCategories();
  };

  const onSelectAll = () => {
    setCategories(categories);
  };

  return (
    <div className={["filters", className ?? ""].join(" ").trim()}>
      <div className="filters__header">
        <h4 className="filters__title">{title}</h4>
        <div className="filters__actions">
          {showClear && (
            <button type="button" className="btn btn--ghost" onClick={onClear}>
              Wissen
            </button>
          )}
          <button type="button" className="btn btn--ghost" onClick={onSelectAll}>
            Alles
          </button>
        </div>
      </div>

      <div className="filters__list" role="group" aria-label={title}>
        {categories.length === 0 && <div className="filters__empty">Geen categorieën beschikbaar.</div>}

        {categories.map((cat) => {
          const active = selectedSet.has(cat);
          const id = `cat-${cat.replace(/\s+/g, "-").toLowerCase()}`;
          return (
            <label key={cat} htmlFor={id} className={["chip", active ? "chip--active" : ""].join(" ")}>
              <input
                id={id}
                type="checkbox"
                checked={active}
                onChange={() => onToggle(cat)}
              />
              <span>{cat}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
};

export default Filters;

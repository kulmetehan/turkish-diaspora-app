// Frontend/src/components/SortBar.tsx

import React from "react";
import { useSortBy, setSort } from "../state/ui";
import type { SortBy } from "../state/ui";

/**
 * Eenvoudige sorteerbalk:
 * - Opties: Afstand | Rating
 * - Schrijft naar centrale UI-store
 */
type Props = {
  className?: string;
  label?: string;
};

const SortBar: React.FC<Props> = ({ className, label = "Sorteer op" }) => {
  const sortBy = useSortBy();

  const onChange: React.ChangeEventHandler<HTMLSelectElement> = (e) => {
    setSort(e.target.value as SortBy);
  };

  return (
    <div className={["sort-bar", className ?? ""].join(" ").trim()}>
      <label className="sort-bar__label" htmlFor="sortBy">
        {label}
      </label>
      <select id="sortBy" value={sortBy} onChange={onChange} className="sort-bar__select">
        <option value="distance">Afstand</option>
        <option value="rating">Rating</option>
      </select>
    </div>
  );
};

export default SortBar;

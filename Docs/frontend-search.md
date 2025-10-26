# Frontend Search & Filters

This document describes the refined search and filters behavior in the bottom sheet.

## Overview
- Search and filtering are client-side against the loaded locations dataset.
- Debounced input (~350ms) prevents spamming recomputations.
- Session-only in-memory LRU cache avoids repeated filter work for recent queries.
- Local suggestions (autocomplete) are derived from location names and category labels/keys.

## Architecture
- `App.tsx` loads locations once and wires UI state.
- `useSearch` consolidates debounced query, filtered results, and suggestions.
- `Filters.tsx` renders search input, suggestion dropdown, and category chips.
- `LocationList` and `MapView` receive the already-filtered list.

## Hook API
```ts
export function useSearch(params: {
  locations: LocationMarker[];
  search: string;
  category: string; // "all" or canonical key
  debounceMs?: number; // default 350
  cacheSize?: number;  // default 30
}): {
  debouncedQuery: string;
  filtered: LocationMarker[];
  suggestions: string[];
}
```

## Debounce Behavior
- Text input is debounced by ~350ms.
- Filtering and suggestions recompute only after the debounce.

## Cache Strategy
- LRU cache keyed by `${query}|${category}` → array of ids.
- Max size ≈30 entries; oldest evicted on overflow.
- Cache clears when the base dataset size changes.
- Cache is session-only (no localStorage).

## Suggestions
- Derived from the in-memory dataset:
  - First pass: location names containing the query.
  - Second pass: category label/key matches if room remains.
- Top 8 unique strings are shown.
- Selecting a suggestion writes it to the search input and applies filtering.

## Component Flow
- `App.tsx` → `useSearch` → `{ filtered, suggestions }`.
- `Filters` receives `search`, `category`, optional `suggestions`, and `onChange`.
- `LocationList` and `MapView` both receive `filtered` to keep the map/list in sync.

## UX & Styling
- `Filters` uses shadcn/ui `Input`, `Button`, `Badge` with lucide icons.
- Clear/reset button inside the input.
- Category selection uses horizontal chips; "Alle" resets to all categories.
- Subtle transitions (`transition-colors`), accessible ARIA, dark/light compatibility.

## Notes
- API calls are not made during search; only the initial load fetches data.
- Order of results follows the loaded dataset (no client sorting added).



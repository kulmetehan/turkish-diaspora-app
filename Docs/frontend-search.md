---
title: Frontend Search & Filters
status: active
last_updated: 2025-11-04
scope: frontend
owners: [tda-ux]
---

# Frontend Search & Filters

Describes the search/filter experience in the map bottom sheet and how the supporting React hooks/components operate.

## Components

| File | Responsibility |
| --- | --- |
| `Frontend/src/App.tsx` | Orchestrates search state via `useSearch`, passes filtered results to map/list components. |
| `Frontend/src/hooks/useSearch.ts` | Debounced search + category filter with in-memory LRU cache and suggestion generation. |
| `Frontend/src/components/Filters.tsx` | Category chips, search input, clear button. |
| `Frontend/src/components/bottom-sheet/` | Presentation components for the draggable bottom sheet. |
| `Frontend/src/components/map/` | Responds to filtered data to update markers and selection. |

## Search flow

1. User types into the search input (`Filters.tsx`).
2. `useSearch` debounces the query (default 350 ms) and caches filtered IDs for up to 30 recent queries.
3. Category filter (`all` or specific key) limits results before markers are passed downstream.
4. Suggestions combine top matching names + category labels (up to 8 entries).
5. Filtered results maintain the order of the server response (no client-side re-sorting to preserve API ordering).

### Available parameters (`useSearch`)

- `search`: raw string from input.
- `category`: canonical category key or `all`.
- `debounceMs`: optional override (default 350 ms).
- `cacheSize`: optional override for LRU size (default 30).

## Bottom sheet behaviour

- Implemented with custom drag/physics helpers under `Frontend/src/components/bottom-sheet/`.
- Snap points: collapsed (`64px`), half (`45vh`), full (`94vh`).
- QA scenarios covered in [`Docs/qa/bottom-sheet-test.md`](./qa/bottom-sheet-test.md).
- Access to filters always available (sticky header) while list scrolls independently when sheet is expanded.

## Filters

- Category chips map to canonical keys from API (`category_key`).
- The search bar supports diacritics; input normalized to lowercase for matches.
- Reset button clears search + category in one action.

## Future enhancements

- Server-side search endpoint (if needed for large datasets).
- Persisting user filters in query string or local storage.
- Additional filters (rating, sources) once backend supports them.

## References

- `useSearch` hook: `Frontend/src/hooks/useSearch.ts`
- Filters component: `Frontend/src/components/Filters.tsx`
- QA checklist: `Docs/qa/bottom-sheet-test.md`

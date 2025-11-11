---
title: Frontend Search & Filters
status: active
last_updated: 2025-11-11
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
| `Frontend/src/components/Filters.tsx` | List view filters (tabs + search + legacy chips). |
| `Frontend/src/components/search/FloatingSearchBar.tsx` | Floating search input with autosuggest and keyboard navigation (map view). |
| `Frontend/src/components/search/CategoryChips.tsx` | Horizontal category carousel rendered under the floating search bar. |
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

## Floating map overlay (F4-S6)

- The map route renders a floating container above Mapbox (`App.tsx`) with:
  - `FloatingSearchBar` (white background, subtle shadow) for debounced search.
  - `CategoryChips` carousel (scrollable, first chip = “All”).
  - View mode tabs (`TabsTrigger` for Kaart/Lijst) to switch between map/list.
- Overlay preserves map interactivity via `pointer-events-none` wrapper and only the UI stack captures pointer events.
- `FloatingSearchBar` reuses `useSearch` suggestions for autosuggest with ↑/↓ navigation, `Enter` apply, `Esc` clear.
- Category chips update the in-memory filter instantly; no network requests are triggered.
- Chips use lucide icons mapped per category key with a `Store` fallback.
- Mobile safe-area insets respected through `pt-[calc(env(safe-area-inset-top)+1rem)]`.

## Bottom sheet behaviour

- Implemented with custom drag/physics helpers under `Frontend/src/components/bottom-sheet/`.
- Snap points: collapsed (`64px`), half (`45vh`), full (`94vh`).
- QA scenarios covered in [`Docs/qa/bottom-sheet-test.md`](./qa/bottom-sheet-test.md).
- Access to filters always available (sticky header) while list scrolls independently when sheet is expanded.

## Filters (list view)

- Category chips map to canonical keys from API (`category_key`).
- The search bar supports diacritics; input normalized to lowercase for matches.
- Reset button clears search + category in one action.

## Theme switcher relocation

- With the legacy header removed, the theme cycle control now lives on `Frontend/src/pages/AccountPage.tsx`.
- Button keeps the same “Theme: {setting}” labelling and order (`light → dark → system`).
- Temporary placement until a dedicated settings screen ships; referenced in Account “Appearance” section.

## Future enhancements

- Server-side search endpoint (if needed for large datasets).
- Persisting user filters in query string or local storage.
- Additional filters (rating, sources) once backend supports them.

## References

- `useSearch` hook: `Frontend/src/hooks/useSearch.ts`
- Filters component: `Frontend/src/components/Filters.tsx`
- QA checklist: `Docs/qa/bottom-sheet-test.md`

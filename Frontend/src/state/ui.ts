// Frontend/src/state/ui.ts
//
// Tiny, dependency-free UI store shared by MapView, List, Filters & SortBar.
// Uses React 18's useSyncExternalStore for safe subscriptions.
// This keeps selection/filter/sort in ONE place to avoid prop-drilling.
//

import { useSyncExternalStore } from "react";

// ---------- Types ----------

export type SortBy = "none" | "distance";

export interface UIState {
  /** Currently selected location id (syncs list <-> map). */
  selectedLocationId: string | null;

  /** Active category filters (strings as they come from the API). */
  selectedCategories: string[];

  /** Current sorting mode for the list. */
  sortBy: SortBy;
}

// ---------- Internal store implementation ----------

const listeners = new Set<() => void>();

// Default UI state
let state: UIState = {
  selectedLocationId: null,
  selectedCategories: [],
  sortBy: "none",
};

function emit() {
  for (const fn of Array.from(listeners)) fn();
}

function setState(patch: Partial<UIState>) {
  state = { ...state, ...patch };
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): UIState {
  return state;
}

// ---------- Public actions (no async/await needed here) ----------

/** Select a location by id (or null to clear). */
export function selectLocation(id: string | null) {
  setState({ selectedLocationId: id });
}

/** Replace the entire category filter list. */
export function setCategories(categories: string[]) {
  // store unique, sorted for stable equality
  const unique = Array.from(new Set(categories)).sort();
  setState({ selectedCategories: unique });
}

/** Toggle a single category on/off. */
export function toggleCategory(category: string) {
  const set = new Set(state.selectedCategories);
  if (set.has(category)) set.delete(category);
  else set.add(category);
  setState({ selectedCategories: Array.from(set).sort() });
}

/** Clear all category filters. */
export function clearCategories() {
  setState({ selectedCategories: [] });
}

/** Set sorting mode. */
export function setSort(sortBy: SortBy) {
  setState({ sortBy });
}

// ---------- Hooks ----------

/** Subscribe to the full UI state. */
export function useUIState(): UIState {
  return useSyncExternalStore(subscribe, getSnapshot);
}

/** Selectors for convenience (avoid rerenders when only part is needed). */
export function useSelectedLocationId(): string | null {
  return useSyncExternalStore(subscribe, () => state.selectedLocationId);
}

export function useSelectedCategories(): string[] {
  return useSyncExternalStore(subscribe, () => state.selectedCategories);
}

export function useSortBy(): SortBy {
  return useSyncExternalStore(subscribe, () => state.sortBy);
}

// ---------- Utilities (testing/dev) ----------

/** Reset to defaults (handy in tests or storybook). */
export function __resetUIState() {
  state = {
    selectedLocationId: null,
    selectedCategories: [],
    sortBy: "none",
  };
  emit();
}

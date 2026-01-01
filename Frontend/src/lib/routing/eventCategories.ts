const CATEGORIES_KEY = "categories";

export const EVENT_CATEGORIES = ["club", "theater", "concert", "familie"] as const;

export type EventCategoryKey = (typeof EVENT_CATEGORIES)[number];

// Event category labels are now translated via i18n
// Use translation keys: events.categories.club, events.categories.theater, etc.
export const EVENT_CATEGORY_LABELS: Record<EventCategoryKey, string> = {
  club: "Club", // Deprecated: use translation keys instead
  theater: "Theater", // Deprecated: use translation keys instead
  concert: "Concert", // Deprecated: use translation keys instead
  familie: "Familie", // Deprecated: use translation keys instead
};

function getHashSearch(): URLSearchParams {
  if (typeof window === "undefined") {
    return new URLSearchParams();
  }
  const hash = window.location.hash ?? "";
  const queryIndex = hash.indexOf("?");
  const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
  return new URLSearchParams(query);
}

function buildHash(params: URLSearchParams): string {
  if (typeof window === "undefined") {
    return "#/";
  }
  const base = window.location.hash.split("?")[0] || "#/";
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

function updateHashParams(mutator: (params: URLSearchParams) => void) {
  if (typeof window === "undefined") return;
  const params = getHashSearch();
  mutator(params);
  const nextHash = buildHash(params);
  if (window.location.hash === nextHash) return;
  window.location.hash = nextHash;
}

function normalizeCategoryValues(values: string[]): EventCategoryKey[] {
  if (!values.length) return [];
  const allowed = new Set<EventCategoryKey>(EVENT_CATEGORIES);
  const deduped: EventCategoryKey[] = [];
  const seen = new Set<string>();

  for (const raw of values) {
    if (!raw) continue;
    const tokens = raw.split(",");
    for (const token of tokens) {
      const normalized = token.trim().toLowerCase() as EventCategoryKey;
      if (!normalized || !allowed.has(normalized) || seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      deduped.push(normalized);
    }
  }

  return deduped;
}

export function readEventCategoriesFromHash(): EventCategoryKey[] {
  const params = getHashSearch();
  const values = params.getAll(CATEGORIES_KEY);
  return normalizeCategoryValues(values);
}

export function writeEventCategoriesToHash(next: string[] | EventCategoryKey[]) {
  const normalized = normalizeCategoryValues(next as string[]);
  updateHashParams((params) => {
    if (!normalized.length) {
      params.delete(CATEGORIES_KEY);
      return;
    }
    params.set(CATEGORIES_KEY, normalized.join(","));
  });
}

export function clearEventCategoriesFromHash() {
  updateHashParams((params) => {
    params.delete(CATEGORIES_KEY);
  });
}

export function subscribeToEventCategoriesHashChange(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}



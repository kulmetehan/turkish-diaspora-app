const CATEGORIES_KEY = "categories";

export const NL_CATEGORIES = ["general", "sport", "economie", "cultuur"] as const;
export const TR_CATEGORIES = ["general", "sport", "economie", "magazin"] as const;

export type NewsCategoryKey = 
  | (typeof NL_CATEGORIES)[number] 
  | (typeof TR_CATEGORIES)[number];

// Map UI category keys → RSS category strings
export const NL_CATEGORY_TO_RSS: Record<string, string> = {
  general: "nl_national",
  sport: "nl_national_sport",
  economie: "nl_national_economie",
  cultuur: "nl_national_cultuur",
};

export const TR_CATEGORY_TO_RSS: Record<string, string> = {
  general: "tr_national",
  sport: "tr_national_sport",
  economie: "tr_national_economie",
  magazin: "tr_national_magazin",
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

function normalizeCategoryValues(values: string[]): NewsCategoryKey[] {
  if (!values.length) return [];
  const allowed = new Set<NewsCategoryKey>([...NL_CATEGORIES, ...TR_CATEGORIES]);
  const deduped: NewsCategoryKey[] = [];
  const seen = new Set<string>();

  for (const raw of values) {
    if (!raw) continue;
    const tokens = raw.split(",");
    for (const token of tokens) {
      const normalized = token.trim().toLowerCase() as NewsCategoryKey;
      if (!normalized || !allowed.has(normalized) || seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      deduped.push(normalized);
    }
  }

  return deduped;
}

export function readNewsCategoriesFromHash(): NewsCategoryKey[] {
  const params = getHashSearch();
  const values = params.getAll(CATEGORIES_KEY);
  return normalizeCategoryValues(values);
}

export function writeNewsCategoriesToHash(next: string[] | NewsCategoryKey[]) {
  const normalized = normalizeCategoryValues(next as string[]);
  updateHashParams((params) => {
    if (!normalized.length) {
      params.delete(CATEGORIES_KEY);
      return;
    }
    params.set(CATEGORIES_KEY, normalized.join(","));
  });
}

export function clearNewsCategoriesFromHash() {
  updateHashParams((params) => {
    params.delete(CATEGORIES_KEY);
  });
}

export function subscribeToNewsCategoriesHashChange(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}


















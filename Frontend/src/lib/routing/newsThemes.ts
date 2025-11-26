const THEMES_KEY = "themes";

export const SUPPORTED_NEWS_THEMES = [
  "politics",
  "economy",
  "culture",
  "religion",
  "sports",
  "security",
] as const;

export type NewsThemeKey = (typeof SUPPORTED_NEWS_THEMES)[number];

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

function normalizeThemeValues(values: string[]): NewsThemeKey[] {
  if (!values.length) return [];
  const allowed = new Set<NewsThemeKey>(SUPPORTED_NEWS_THEMES);
  const deduped: NewsThemeKey[] = [];
  const seen = new Set<string>();

  for (const raw of values) {
    if (!raw) continue;
    const tokens = raw.split(",");
    for (const token of tokens) {
      const normalized = token.trim().toLowerCase() as NewsThemeKey;
      if (!normalized || !allowed.has(normalized) || seen.has(normalized)) {
        continue;
      }
      seen.add(normalized);
      deduped.push(normalized);
    }
  }

  return deduped;
}

export function readNewsThemesFromHash(): NewsThemeKey[] {
  const params = getHashSearch();
  const values = params.getAll(THEMES_KEY);
  return normalizeThemeValues(values);
}

export function writeNewsThemesToHash(next: string[] | NewsThemeKey[]) {
  const normalized = normalizeThemeValues(next as string[]);
  updateHashParams((params) => {
    if (!normalized.length) {
      params.delete(THEMES_KEY);
      return;
    }
    params.set(THEMES_KEY, normalized.join(","));
  });
}

export function clearNewsThemesFromHash() {
  updateHashParams((params) => {
    params.delete(THEMES_KEY);
  });
}

export function subscribeToNewsThemesHashChange(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}





// Frontend/src/lib/routing/viewMode.ts
export type ViewMode = "list" | "map";

const VIEW_KEY = "view";
const FOCUS_KEY = "focus";
const DEFAULT_VIEW: ViewMode = "map";

function getHashSearch(): URLSearchParams {
  const hash = typeof window === "undefined" ? "" : window.location.hash ?? "";
  const queryIndex = hash.indexOf("?");
  const query = queryIndex >= 0 ? hash.slice(queryIndex + 1) : "";
  return new URLSearchParams(query);
}

function buildHash(params: URLSearchParams): string {
  const base = typeof window === "undefined" ? "#/" : window.location.hash.split("?")[0] || "#/";
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

export function readViewMode(): ViewMode {
  const params = getHashSearch();
  const raw = params.get(VIEW_KEY)?.toLowerCase();
  return raw === "list" ? "list" : DEFAULT_VIEW;
}

export function readFocusId(): string | null {
  const params = getHashSearch();
  const raw = params.get(FOCUS_KEY);
  return raw ? String(raw) : null;
}

export function writeViewMode(next: ViewMode) {
  updateHashParams((params) => {
    params.set(VIEW_KEY, next);
  });
}

export function writeFocusId(id: string) {
  updateHashParams((params) => {
    params.set(FOCUS_KEY, String(id));
  });
}

export function clearFocusId() {
  updateHashParams((params) => {
    params.delete(FOCUS_KEY);
  });
}

export function onHashChange(callback: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}



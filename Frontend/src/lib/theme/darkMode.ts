const STORAGE_KEY = "tda:theme"; // 'light' | 'dark' | 'system'
export type ThemeSetting = "light" | "dark" | "system";

function apply(theme: ThemeSetting) {
  const root = document.documentElement;
  const isSystemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const effectiveDark = theme === "dark" || (theme === "system" && isSystemDark);
  root.classList.toggle("dark", effectiveDark);
}

export function initTheme() {
  const saved = (localStorage.getItem(STORAGE_KEY) as ThemeSetting) || "system";
  apply(saved);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    const current = (localStorage.getItem(STORAGE_KEY) as ThemeSetting) || "system";
    if (current === "system") apply("system");
  });
}

export function setTheme(next: ThemeSetting) {
  localStorage.setItem(STORAGE_KEY, next);
  apply(next);
}

export function getTheme(): ThemeSetting {
  return ((localStorage.getItem(STORAGE_KEY) as ThemeSetting) || "system");
}

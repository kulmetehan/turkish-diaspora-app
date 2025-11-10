// src/i18n/index.ts

const STORAGE_KEY = "tda-language";
const SUPPORTED = ["nl", "en"] as const;
type SupportedLang = (typeof SUPPORTED)[number];

let initialized = false;
let currentLanguage: SupportedLang = "nl";

const listeners = new Set<(lang: SupportedLang) => void>();

function normaliseLanguage(value: string | null | undefined): SupportedLang {
  if (!value) return "nl";
  const lower = value.toLowerCase();
  const match = SUPPORTED.find((lang) => lower.startsWith(lang));
  return match ?? "nl";
}

export function initI18n(): SupportedLang {
  if (initialized) return currentLanguage;
  initialized = true;

  if (typeof window !== "undefined" && typeof window.localStorage !== "undefined") {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    currentLanguage = normaliseLanguage(stored);
    window.localStorage.setItem(STORAGE_KEY, currentLanguage);
  }

  return currentLanguage;
}

export function getCurrentLanguage(): SupportedLang {
  if (!initialized) {
    initI18n();
  }
  return currentLanguage;
}

export function setLanguage(next?: string | null) {
  const target = normaliseLanguage(next);
  if (target === currentLanguage) return;
  currentLanguage = target;
  if (typeof window !== "undefined" && typeof window.localStorage !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, currentLanguage);
  }
  listeners.forEach((listener) => {
    try {
      listener(currentLanguage);
    } catch {
      /* ignore listener errors */
    }
  });
}

export function subscribeLanguage(listener: (lang: SupportedLang) => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getAcceptLanguageHeader(): string {
  const lang = getCurrentLanguage();
  return lang === "nl" ? "nl-NL" : lang === "en" ? "en-US" : lang;
}



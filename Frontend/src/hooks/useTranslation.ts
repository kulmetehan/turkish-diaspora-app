import { useState, useEffect, useCallback } from "react";
import { getCurrentLanguage, setLanguage, subscribeLanguage, type SupportedLang } from "@/i18n";
import { nl } from "@/i18n/translations/nl";
import { tr } from "@/i18n/translations/tr";
import type { TranslationKey } from "@/i18n/types";

const translations = {
  nl,
  tr,
} as const;

// Helper function to get nested value from object using dot notation
function getNestedValue(obj: any, path: string): string {
  const keys = path.split(".");
  let value = obj;
  for (const key of keys) {
    if (value === null || value === undefined) {
      return path; // Fallback to key if path doesn't exist
    }
    value = value[key];
  }
  return typeof value === "string" ? value : path;
}

export function useTranslation() {
  const [lang, setLangState] = useState<SupportedLang>(getCurrentLanguage());

  useEffect(() => {
    const unsubscribe = subscribeLanguage((newLang) => {
      setLangState(newLang);
    });
    return unsubscribe;
  }, []);

  const t = useCallback(
    (key: TranslationKey): string => {
      const translation = translations[lang];
      if (!translation) {
        return getNestedValue(translations.nl, key) || key;
      }
      const value = getNestedValue(translation, key);
      // Fallback to Dutch if translation is missing
      if (value === key && lang !== "nl") {
        return getNestedValue(translations.nl, key) || key;
      }
      return value;
    },
    [lang]
  );

  return {
    t,
    lang,
    setLanguage: (newLang: SupportedLang) => {
      setLanguage(newLang);
      setLangState(newLang);
    },
  };
}



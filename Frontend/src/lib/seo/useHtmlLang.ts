// Frontend/src/lib/seo/useHtmlLang.ts
// Hook voor dynamische HTML lang attribute updates

import { useEffect } from "react";
import { getCurrentLanguage, subscribeLanguage } from "@/i18n";

/**
 * Hook die de HTML lang attribute update op basis van i18n state
 */
export function useHtmlLang() {
  useEffect(() => {
    // Set initial lang
    const updateLang = (lang: string) => {
      if (typeof document !== "undefined") {
        document.documentElement.lang = lang;
      }
    };
    
    // Set initial language
    const currentLang = getCurrentLanguage();
    updateLang(currentLang);
    
    // Subscribe to language changes
    const unsubscribe = subscribeLanguage((lang) => {
      updateLang(lang);
    });
    
    return unsubscribe;
  }, []);
}







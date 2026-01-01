// Language Switcher Component - Facebook-style dropdown
import { useState, useRef, useEffect } from "react";
import { useTranslation } from "@/hooks/useTranslation";
import { Icon } from "@/components/Icon";
import { cn } from "@/lib/ui/cn";

export function LanguageSwitcher() {
  const { t, lang, setLanguage } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }
  }, [isOpen]);

  const languages = [
    { code: "nl" as const, label: t("onboarding.language.dutch") },
    { code: "tr" as const, label: t("onboarding.language.turkish") },
  ];

  const currentLanguage = languages.find((l) => l.code === lang) || languages[0];

  const handleLanguageSelect = (code: "nl" | "tr") => {
    setLanguage(code);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-lg",
          "bg-surface-muted/50 hover:bg-surface-muted",
          "text-sm font-medium text-foreground",
          "transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
        )}
        aria-label="Selecteer taal"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Icon name="Globe" className="h-4 w-4" aria-hidden />
        <span>{currentLanguage.label}</span>
        <Icon
          name={isOpen ? "ChevronUp" : "ChevronDown"}
          className="h-4 w-4 text-muted-foreground"
          aria-hidden
        />
      </button>

      {isOpen && (
        <div
          className={cn(
            "absolute top-full left-0 mt-2 min-w-[180px]",
            "bg-background border border-border rounded-lg shadow-lg",
            "z-50 overflow-hidden",
            "animate-in fade-in-0 zoom-in-95 duration-200"
          )}
          role="menu"
        >
          {languages.map((language) => {
            const isSelected = language.code === lang;
            return (
              <button
                key={language.code}
                type="button"
                onClick={() => handleLanguageSelect(language.code)}
                className={cn(
                  "w-full px-4 py-2.5 text-left text-sm",
                  "flex items-center justify-between gap-3",
                  "transition-colors",
                  isSelected
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-foreground hover:bg-muted"
                )}
                role="menuitem"
              >
                <span>{language.label}</span>
                {isSelected && (
                  <Icon name="Check" className="h-4 w-4 text-primary" aria-hidden />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}



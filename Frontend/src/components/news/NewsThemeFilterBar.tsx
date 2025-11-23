import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/ui/cn";
import {
  SUPPORTED_NEWS_THEMES,
  type NewsThemeKey,
} from "@/lib/routing/newsThemes";

const THEME_LABELS: Record<NewsThemeKey, string> = {
  politics: "Politiek",
  economy: "Economie",
  culture: "Cultuur",
  religion: "Religie",
  sports: "Sport",
  security: "Veiligheid",
};

export interface NewsThemeFilterBarProps {
  selected: NewsThemeKey[];
  onChange: (themes: NewsThemeKey[]) => void;
  onClear?: () => void;
  className?: string;
}

export function NewsThemeFilterBar({
  selected,
  onChange,
  onClear,
  className,
}: NewsThemeFilterBarProps) {
  const normalizedSelection = useMemo(() => {
    const seen = new Set<NewsThemeKey>();
    const result: NewsThemeKey[] = [];
    for (const theme of selected) {
      if (!theme || seen.has(theme)) continue;
      seen.add(theme);
      result.push(theme);
    }
    return result;
  }, [selected]);

  const handleToggle = (theme: NewsThemeKey) => {
    const isActive = normalizedSelection.includes(theme);
    const next = isActive
      ? normalizedSelection.filter((value) => value !== theme)
      : [...normalizedSelection, theme];
    onChange(next);
  };

  const handleClear = () => {
    if (!normalizedSelection.length) return;
    if (onClear) {
      onClear();
    } else {
      onChange([]);
    }
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border bg-card p-3",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          Thema filters
        </span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
          onClick={handleClear}
          disabled={!normalizedSelection.length}
        >
          Filters wissen
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUPPORTED_NEWS_THEMES.map((theme) => {
          const active = normalizedSelection.includes(theme);
          return (
            <button
              key={theme}
              type="button"
              role="checkbox"
              aria-checked={active}
              onClick={() => handleToggle(theme)}
              className={cn(
                "inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                active
                  ? "border-brand-red bg-brand-redSoft text-primary-foreground shadow-sm"
                  : "border-border bg-background text-foreground hover:bg-muted",
              )}
            >
              {THEME_LABELS[theme]}
            </button>
          );
        })}
      </div>
    </div>
  );
}



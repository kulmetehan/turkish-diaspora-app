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
        "flex flex-col gap-3 rounded-3xl border border-border bg-surface-raised p-4 text-foreground shadow-soft",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Thema filters
        </span>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground"
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
                "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-white/70 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent",
                active
                  ? "border-transparent bg-[hsl(var(--brand-red-strong))] text-brand-white shadow-[0_12px_30px_rgba(0,0,0,0.35)]"
                  : "border-border bg-surface-muted text-foreground hover:bg-surface-muted/80",
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



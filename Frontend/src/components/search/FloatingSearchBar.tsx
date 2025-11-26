import { useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";

type FloatingSearchBarProps = {
  value: string;
  onValueChange: (value: string) => void;
  onClear: () => void;
  suggestions?: string[];
  ariaLabel?: string;
  placeholder?: string;
  loading?: boolean;
  className?: string;
  inputId?: string;
};

export function FloatingSearchBar({
  value,
  onValueChange,
  onClear,
  suggestions,
  ariaLabel = "Search locations",
  placeholder = "Zoek op naam of categorie…",
  loading,
  className,
  inputId,
}: FloatingSearchBarProps) {
  const generatedInputId = useId();
  const resolvedInputId = inputId ?? generatedInputId;
  const listboxId = `${resolvedInputId}-suggestions`;
  const suggestBoxRef = useRef<HTMLDivElement | null>(null);
  const [openSuggest, setOpenSuggest] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const trimmed = value.trim();
  const hasInput = trimmed.length > 0;
  const normalizedSuggestions = useMemo(() => suggestions ?? [], [suggestions]);
  const showSuggestions = Boolean(
    openSuggest && normalizedSuggestions.length && hasInput,
  );

  return (
    <div className={cn("relative w-full", className)} ref={suggestBoxRef}>
      <label htmlFor={resolvedInputId} className="sr-only">
        {ariaLabel}
      </label>
      <div className="relative">
        <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-2 shadow-soft transition focus-within:ring-2 focus-within:ring-primary/20 focus-within:ring-offset-2 focus-within:ring-offset-background">
          <span className="text-muted-foreground">
            <Search className="h-5 w-5" aria-hidden />
          </span>
          <Input
            id={resolvedInputId}
            role="combobox"
            aria-expanded={showSuggestions}
            aria-controls={showSuggestions ? listboxId : undefined}
            aria-autocomplete="list"
            autoComplete="off"
            placeholder={placeholder}
            value={value}
            className="h-12 flex-1 border-0 bg-transparent px-0 py-0 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0"
            onChange={(event) => {
              onValueChange(event.target.value);
              setOpenSuggest(true);
              setActiveIndex(0);
            }}
            onFocus={() => setOpenSuggest(true)}
            onBlur={() => {
              window.setTimeout(() => setOpenSuggest(false), 120);
            }}
            onKeyDown={(event) => {
              if (!normalizedSuggestions.length) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setOpenSuggest(true);
                setActiveIndex((index) =>
                  Math.min(index + 1, normalizedSuggestions.length - 1),
                );
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setOpenSuggest(true);
                setActiveIndex((index) => Math.max(index - 1, 0));
              } else if (event.key === "Enter") {
                if (!showSuggestions) return;
                event.preventDefault();
                const suggestion = normalizedSuggestions[activeIndex];
                if (suggestion) {
                  onValueChange(suggestion);
                  setOpenSuggest(false);
                }
              } else if (event.key === "Escape") {
                if (value) {
                  onClear();
                }
                setOpenSuggest(false);
              }
            }}
          />
          {loading ? (
            <span className="text-xs font-semibold text-muted-foreground">…</span>
          ) : null}
          {value ? (
            <button
              type="button"
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition-colors",
                "hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
              )}
              aria-label="Zoekveld wissen"
              onClick={() => {
                onClear();
                setOpenSuggest(false);
                setActiveIndex(0);
              }}
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>

      {showSuggestions ? (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Zoek suggesties"
          className="absolute z-20 mt-3 w-full overflow-hidden rounded-2xl border border-border bg-card text-foreground shadow-card"
        >
          <div className="max-h-60 overflow-auto py-1 text-sm">
            {normalizedSuggestions.map((suggestion, index) => {
              const active = index === activeIndex;
              return (
                <button
                  key={`${suggestion}-${index}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={cn(
                    "flex w-full items-center justify-between px-3 py-2 text-left",
                    "hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:bg-accent/80",
                    active && "bg-accent/60",
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    onValueChange(suggestion);
                    setOpenSuggest(false);
                  }}
                >
                  <span>{suggestion}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}



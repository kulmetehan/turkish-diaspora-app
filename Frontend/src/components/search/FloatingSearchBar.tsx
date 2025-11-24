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
};

export function FloatingSearchBar({
  value,
  onValueChange,
  onClear,
  suggestions,
  ariaLabel = "Search locations",
  placeholder = "Zoek op naam of categorie…",
  loading,
}: FloatingSearchBarProps) {
  const inputId = useId();
  const listboxId = `${inputId}-suggestions`;
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
    <div className="relative w-full" ref={suggestBoxRef}>
      <label htmlFor={inputId} className="sr-only">
        {ariaLabel}
      </label>
      <div className="relative">
        <span className="absolute inset-y-0 left-3 flex items-center text-muted-foreground">
          <Search className="h-4 w-4" aria-hidden />
        </span>
        <Input
          id={inputId}
          role="combobox"
          aria-expanded={showSuggestions}
          aria-controls={showSuggestions ? listboxId : undefined}
          aria-autocomplete="list"
          autoComplete="off"
          placeholder={placeholder}
          value={value}
          className="h-12 rounded-xl border border-border bg-card pl-9 pr-12 text-base text-foreground placeholder:text-muted-foreground shadow-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
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
        {value ? (
          <button
            type="button"
            className={cn(
              "absolute inset-y-0 right-3 flex items-center text-muted-foreground transition-colors",
              "hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
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
        {loading ? (
          <span className="pointer-events-none absolute inset-y-0 right-10 flex items-center text-xs text-muted-foreground">
            …
          </span>
        ) : null}
      </div>

      {showSuggestions ? (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Zoek suggesties"
          className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-border bg-card text-foreground shadow-xl"
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



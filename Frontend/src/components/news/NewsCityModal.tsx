import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import type { NewsCity } from "@/api/news";
import { searchNewsCities } from "@/api/news";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type {
  CityLabel,
  CityLabelMap,
  CityPreferences,
  CityRecommendations,
} from "@/hooks/useNewsCityPreferences";
import { cn } from "@/lib/ui/cn";

type CountryCode = "nl" | "tr";
type CitySuggestion = Pick<
  NewsCity,
  "cityKey" | "name" | "country" | "province" | "parentKey"
>;

const MAX_SELECTIONS = 2;

interface NewsCityModalProps {
  isOpen: boolean;
  options: CityRecommendations | null;
  preferences: CityPreferences;
  cityLabels: CityLabelMap;
  onRememberCities: (cities: CityLabel[] | NewsCity[] | CityRecommendations | null) => void;
  onSave: (prefs: CityPreferences) => void;
  onClose: () => void;
}

export function NewsCityModal({
  isOpen,
  options,
  preferences,
  cityLabels,
  onRememberCities,
  onSave,
  onClose,
}: NewsCityModalProps) {
  const [draft, setDraft] = useState<CityPreferences>(preferences);

  useEffect(() => {
    setDraft(preferences);
  }, [preferences]);

  const recommended = useMemo<CityRecommendations>(
    () =>
      options ?? {
        nl: [],
        tr: [],
      },
    [options],
  );

  const handleAddCity = (country: CountryCode, city: CitySuggestion) => {
    setDraft((prev) => {
      const normalized = city.cityKey.toLowerCase();
      const existing = prev[country];
      if (existing.includes(normalized) || existing.length >= MAX_SELECTIONS) {
        return prev;
      }
      return {
        ...prev,
        [country]: [...existing, normalized],
      };
    });
    onRememberCities([
      {
        key: city.cityKey.toLowerCase(),
        name: city.name,
        country,
        province: city.province,
      },
    ]);
  };

  const handleRemoveCity = (country: CountryCode, cityKey: string) => {
    setDraft((prev) => ({
      ...prev,
      [country]: prev[country].filter((key) => key !== cityKey),
    }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Kies je steden</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Selecteer maximaal twee steden per land. Deze voorkeuren worden lokaal opgeslagen.
        </p>
        <div className="mt-4 grid gap-6 lg:grid-cols-2">
          <CityAutosuggestColumn
            title="Nederland"
            country="nl"
            selected={draft.nl}
            cityLabels={cityLabels}
            recommended={recommended.nl}
            onAddCity={handleAddCity}
            onRemoveCity={handleRemoveCity}
          />
          <CityAutosuggestColumn
            title="Turkije"
            country="tr"
            selected={draft.tr}
            cityLabels={cityLabels}
            recommended={recommended.tr}
            onAddCity={handleAddCity}
            onRemoveCity={handleRemoveCity}
          />
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Annuleren
          </Button>
          <Button type="button" onClick={() => onSave(draft)}>
            Opslaan
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface CityAutosuggestColumnProps {
  title: string;
  country: CountryCode;
  selected: string[];
  cityLabels: CityLabelMap;
  recommended: NewsCity[];
  onAddCity: (country: CountryCode, city: CitySuggestion) => void;
  onRemoveCity: (country: CountryCode, cityKey: string) => void;
}

function CityAutosuggestColumn({
  title,
  country,
  selected,
  cityLabels,
  recommended,
  onAddCity,
  onRemoveCity,
}: CityAutosuggestColumnProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CitySuggestion[]>([]);
  const [isSearching, setSearching] = useState(false);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setSearching(false);
      return;
    }
    const controller = new AbortController();
    const handle = window.setTimeout(async () => {
      setSearching(true);
      try {
        const data = await searchNewsCities({
          country,
          q: trimmed,
          limit: 10,
          signal: controller.signal,
        });
        setResults(data);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          console.error("Failed to search news cities", error);
        }
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
  }, [country, query]);

  const canAddMore = selected.length < MAX_SELECTIONS;
  const disableMessage =
    selected.length >= MAX_SELECTIONS ? "Je hebt de limiet van twee steden bereikt." : undefined;

  return (
    <div className="rounded-2xl border border-border/70 p-4">
      <p className="mb-3 text-sm font-semibold">{title}</p>
      <div className="flex flex-wrap gap-2">
        {selected.map((key) => (
          <SelectedCityChip
            key={key}
            label={cityLabels[key]?.name ?? key}
            onRemove={() => onRemoveCity(country, key)}
          />
        ))}
        {selected.length === 0 ? (
          <span className="text-xs text-muted-foreground">Nog geen steden gekozen.</span>
        ) : null}
      </div>

      <div className="mt-4 space-y-2">
        <Input
          value={query}
          placeholder="Typ een stad (min. 2 letters)…"
          onChange={(event) => setQuery(event.target.value)}
        />
        {isSearching ? <p className="text-xs text-muted-foreground">Zoeken…</p> : null}
        {disableMessage ? (
          <p className="text-xs text-muted-foreground">{disableMessage}</p>
        ) : null}
        {!isSearching && results.length > 0 ? (
          <div className="space-y-1">
            {results.map((city) => {
              if (!city.cityKey) {
                return null;
              }
              const normalized = city.cityKey.toLowerCase();
              const alreadySelected = selected.includes(normalized);
              return (
                <SuggestionButton
                  key={`${country}-suggestion-${city.cityKey}`}
                  disabled={alreadySelected || !canAddMore}
                  onClick={() => {
                    onAddCity(country, city);
                    setQuery("");
                    setResults([]);
                  }}
                >
                  <span>{city.name}</span>
                  {city.country === "tr" && city.province ? (
                    <span className="text-xs text-muted-foreground">({city.province})</span>
                  ) : city.province ? (
                    <span className="text-xs text-muted-foreground">{city.province}</span>
                  ) : null}
                </SuggestionButton>
              );
            })}
          </div>
        ) : null}
      </div>

      {recommended.length ? (
        <div className="mt-4 space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Aanbevolen</p>
          <div className="flex flex-wrap gap-2">
            {recommended.map((city) => {
              if (!city.cityKey) return null;
              const normalized = city.cityKey.toLowerCase();
              return (
                <Button
                  key={`${country}-recommended-${city.cityKey}`}
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={!canAddMore || selected.includes(normalized)}
                  onClick={() =>
                    onAddCity(country, {
                      cityKey: city.cityKey,
                      name: city.name,
                      country: city.country,
                      province: city.province,
                    })
                  }
                >
                  <div className="flex flex-col leading-tight">
                    <span>{city.name}</span>
                    {city.country === "tr" && city.province ? (
                      <span className="text-[11px] text-muted-foreground">{city.province}</span>
                    ) : null}
                  </div>
                </Button>
              );
            })}
          </div>
        </div>
      ) : null}
      <p className="mt-4 text-xs text-muted-foreground">{selected.length}/2 gekozen</p>
    </div>
  );
}

function SelectedCityChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-foreground">
      {label}
      <button
        type="button"
        onClick={onRemove}
        className="rounded-full p-0.5 text-muted-foreground transition hover:text-foreground"
        aria-label={`Verwijder ${label}`}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function SuggestionButton({
  children,
  disabled,
  onClick,
}: {
  children: ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between rounded-xl border border-border px-3 py-2 text-left text-sm transition",
        disabled ? "cursor-not-allowed opacity-50" : "hover:bg-surface-muted",
      )}
    >
      {children}
    </button>
  );
}

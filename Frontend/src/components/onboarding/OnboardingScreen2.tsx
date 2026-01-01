// Onboarding Screen 2: Woonplaats Picker
import type { NewsCity } from "@/api/news";
import { searchNewsCities } from "@/api/news";
import woonplaatsBg from "@/assets/woonplaats-bg.png";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/ui/cn";
import { useTranslation } from "@/hooks/useTranslation";
import { useEffect, useRef, useState } from "react";

export interface OnboardingScreen2Props {
  onNext: (data: { home_city: string; home_region: string; home_city_key: string }) => void;
  onPrevious?: () => void;
}

export function OnboardingScreen2({ onNext, onPrevious }: OnboardingScreen2Props) {
  const { t } = useTranslation();
  const [selectedCity, setSelectedCity] = useState<NewsCity | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<NewsCity[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Search cities when query changes
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(async () => {
      setIsSearching(true);
      try {
        // Search only in NL for woonplaats
        const nlResults = await searchNewsCities({
          country: "nl",
          q: trimmed,
          limit: 20,
          signal: controller.signal,
        }).catch(() => []);
        // Filter to ensure only NL cities are shown (safety check)
        const filteredResults = nlResults.filter(city => city.country === "nl");
        setSearchResults(filteredResults);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          console.error("Failed to search cities", error);
        }
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => {
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [searchQuery]);

  const handleCitySelect = (city: NewsCity, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // Dismiss keyboard immediately
    inputRef.current?.blur();

    // Clear search results and query for clean UI
    setSearchResults([]);
    setSearchQuery("");

    // Set selected city
    setSelectedCity(city);

    // Automatically proceed to next step after a short delay
    // This ensures the keyboard dismisses and UI updates smoothly
    setTimeout(() => {
      onNext({
        home_city: city.name,
        home_region: city.province || city.country.toUpperCase(),
        home_city_key: city.cityKey.toLowerCase(),
      });
    }, 150);
  };

  const handleNext = () => {
    if (selectedCity) {
      onNext({
        home_city: selectedCity.name,
        home_region: selectedCity.province || selectedCity.country.toUpperCase(),
        home_city_key: selectedCity.cityKey.toLowerCase(),
      });
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-background" style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex-shrink-0 flex flex-col items-center justify-center px-6 pt-12 pb-6">
        <img
          src={woonplaatsBg}
          alt="Woonplaats mascotte"
          className="h-32 w-32 object-contain mb-4"
        />
        <h2 className="mb-2 text-2xl font-gilroy font-bold text-foreground text-center">
          {t("onboarding.homeCity.title")}
        </h2>
        <p className="text-sm font-gilroy font-normal text-muted-foreground text-center whitespace-pre-line">
          {t("onboarding.homeCity.subtitle")}
        </p>
      </div>

      {/* Search input */}
      <div className="flex-shrink-0 px-6 pb-4">
        <Input
          ref={inputRef}
          type="text"
          placeholder={t("onboarding.homeCity.placeholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full text-base"
          style={{ fontSize: '16px' }}
        />
      </div>

      {/* City list - positioned above footer */}
      <div
        className="flex-1 overflow-y-auto px-6 pb-40 relative z-[60] bg-background"
        style={{
          minHeight: 0,
        }}
      >
        <div className="space-y-2">
          {isSearching ? (
            <div className="py-8 text-center text-muted-foreground">
              {t("onboarding.homeCity.searching")}
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map((city) => (
              <button
                key={city.cityKey}
                onClick={(e) => handleCitySelect(city, e)}
                onMouseDown={(e) => e.preventDefault()}
                className={cn(
                  "w-full rounded-lg border p-4 text-left transition-all cursor-pointer relative",
                  selectedCity?.cityKey === city.cityKey
                    ? "border-primary bg-primary/10"
                    : "border-border bg-card hover:bg-muted"
                )}
                style={{ pointerEvents: 'auto' }}
              >
                <div className="font-semibold text-foreground">{city.name}</div>
                <div className="text-sm text-muted-foreground">
                  {city.province || city.country.toUpperCase()}
                </div>
              </button>
            ))
          ) : searchQuery.trim().length >= 2 ? (
            <div className="py-8 text-center text-muted-foreground">
              {t("onboarding.homeCity.noResults")}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground">
              {t("onboarding.homeCity.minChars")}
            </div>
          )}
        </div>
      </div>

      {/* Footer with CTA */}
      <div
        className="px-6 pt-4 border-t border-border/50 bg-background z-50 shadow-lg"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          paddingBottom: 'calc(2rem + env(safe-area-inset-bottom))',
          pointerEvents: 'none',
        }}
      >
        {selectedCity && (
          <div className="mb-4 text-center" style={{ pointerEvents: 'auto' }}>
            <p className="text-sm font-medium text-foreground">
              {t("onboarding.homeCity.selected")} {selectedCity.name}
            </p>
            {selectedCity.province && (
              <p className="text-xs text-muted-foreground">{selectedCity.province}</p>
            )}
          </div>
        )}
        <div className="flex gap-4" style={{ pointerEvents: 'auto' }}>
          {onPrevious && (
            <Button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('[OnboardingScreen2] Vorige button clicked');
                onPrevious();
              }}
              size="lg"
              variant="outline"
              className="flex-1"
              style={{ position: 'relative', zIndex: 11, pointerEvents: 'auto', cursor: 'pointer' }}
              aria-label={t("onboarding.homeCity.previous")}
            >
              {t("onboarding.homeCity.previous")}
            </Button>
          )}
          <Button
            onClick={handleNext}
            size="lg"
            variant="default"
            className={onPrevious ? "flex-1" : "w-full"}
            disabled={!selectedCity}
            style={{ position: 'relative', zIndex: 11, pointerEvents: 'auto' }}
            aria-label={t("onboarding.homeCity.continue")}
          >
            {t("onboarding.homeCity.continue")}
          </Button>
        </div>
      </div>
    </div>
  );
}







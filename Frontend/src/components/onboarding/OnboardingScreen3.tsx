// Onboarding Screen 3: Memleket Selector
import type { NewsCity } from "@/api/news";
import { searchNewsCities } from "@/api/news";
import memleketBg from "@/assets/memleket-bg.png";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/ui/cn";
import { useEffect, useRef, useState } from "react";

export interface OnboardingScreen3Props {
  onNext: (data: { memleket: string[] | null }) => void;
}

export function OnboardingScreen3({ onNext }: OnboardingScreen3Props) {
  const [selectedCities, setSelectedCities] = useState<NewsCity[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<NewsCity[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showMultiple, setShowMultiple] = useState(true); // Start directly in multiple mode
  const inputRef = useRef<HTMLInputElement>(null);

  // Search Turkish cities (including ilçe's) when query changes
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
        const results = await searchNewsCities({
          country: "tr",
          q: trimmed,
          limit: 50, // Get more results to include ilçe's
          signal: controller.signal,
        });
        setSearchResults(results);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          console.error("Failed to search Turkish cities", error);
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

  const handleCityToggle = (city: NewsCity, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    // Dismiss keyboard immediately
    inputRef.current?.blur();

    // Check if city is already selected
    const isAlreadySelected = selectedCities.some((c) => c.cityKey === city.cityKey);

    if (isAlreadySelected) {
      // If already selected, remove it (toggle off)
      setSelectedCities((prev) => prev.filter((c) => c.cityKey !== city.cityKey));
      return;
    }

    // Add city to selection
    const newSelectedCities = [...selectedCities, city];
    setSelectedCities(newSelectedCities);

    // Clear search query and results for clean UI
    setSearchQuery("");
    setSearchResults([]);

    // Automatically proceed to next step after a short delay
    // This ensures the keyboard dismisses and UI updates smoothly
    setTimeout(() => {
      const cityKeys = newSelectedCities.map((c) => c.cityKey.toLowerCase());
      onNext({ memleket: cityKeys });
    }, 150);
  };

  const handleMultiple = () => {
    setShowMultiple(true);
  };

  const handleSkip = () => {
    onNext({ memleket: null });
  };

  const handleNext = () => {
    if (showMultiple && selectedCities.length > 0) {
      // Extract city keys (normalized)
      const cityKeys = selectedCities.map((city) => city.cityKey.toLowerCase());
      onNext({ memleket: cityKeys });
    } else if (!showMultiple) {
      // If not in multiple mode, treat as skip
      onNext({ memleket: null });
    }
  };

  if (!showMultiple) {
    return (
      <div className="fixed inset-0 z-[100] flex flex-col bg-background">
        {/* Header */}
        <div className="flex flex-col items-center justify-center px-6 pt-12 pb-6">
          <img
            src={memleketBg}
            alt="Memleket mascotte"
            className="h-32 w-32 object-contain mb-4"
          />
          <h2 className="mb-2 text-2xl font-gilroy font-bold text-foreground text-center">
            En je roots?
          </h2>
          <p className="text-sm font-gilroy font-normal text-muted-foreground text-center">
            Iedereen heeft er één.<br />
            Of meer.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex-1 flex flex-col items-center justify-center px-6 space-y-4">
          <Button
            onClick={handleMultiple}
            size="lg"
            variant="default"
            className="w-full font-gilroy"
          >
            Meerdere
          </Button>
          <Button
            onClick={handleSkip}
            size="lg"
            variant="outline"
            className="w-full font-gilroy"
          >
            Sla over
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-background">
      {/* Header */}
      <div className="flex flex-col items-center justify-center px-6 pt-12 pb-6">
        <img
          src={memleketBg}
          alt="Memleket mascotte"
          className="h-32 w-32 object-contain mb-4"
        />
        <h2 className="mb-2 text-2xl font-gilroy font-bold text-foreground text-center">
          En je roots?
        </h2>
        <p className="text-sm font-gilroy font-normal text-muted-foreground text-center">
          Hemşerim Memleket Nire?
        </p>
      </div>

      {/* Search input */}
      <div className="px-6 pb-4">
        <Input
          ref={inputRef}
          type="text"
          placeholder="Zoek stad of ilçe... in Turkije"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full text-base"
          style={{ fontSize: '16px' }}
        />
      </div>

      {/* City list - positioned above footer */}
      <div className="flex-1 overflow-y-auto px-6 pb-40 relative z-[60] bg-background" style={{ minHeight: 0 }}>
        <div className="space-y-2">
          {isSearching ? (
            <div className="py-8 text-center text-muted-foreground">
              Zoeken...
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map((city) => {
              const isSelected = selectedCities.some((c) => c.cityKey === city.cityKey);
              return (
                <button
                  key={city.cityKey}
                  onClick={(e) => handleCityToggle(city, e)}
                  onMouseDown={(e) => e.preventDefault()}
                  className={cn(
                    "w-full rounded-lg border p-4 text-left transition-all cursor-pointer relative",
                    isSelected
                      ? "border-primary bg-primary/10"
                      : "border-border bg-card hover:bg-muted"
                  )}
                  style={{ pointerEvents: 'auto' }}
                >
                  <div className="font-semibold text-foreground">
                    {city.name}
                  </div>
                  {city.province && (
                    <div className="text-sm text-muted-foreground">
                      {city.province}
                    </div>
                  )}
                  {isSelected && (
                    <div className="mt-1 text-sm text-primary">✓ Geselecteerd</div>
                  )}
                </button>
              );
            })
          ) : searchQuery.trim().length >= 2 ? (
            <div className="py-8 text-center text-muted-foreground">
              Geen steden gevonden
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground">
              Typ minimaal 2 letters om te zoeken
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
        {selectedCities.length > 0 && (
          <div className="mb-4 text-center" style={{ pointerEvents: 'auto' }}>
            <p className="text-sm font-medium text-foreground">
              {selectedCities.length} stad{selectedCities.length > 1 ? 'en' : ''} geselecteerd
            </p>
          </div>
        )}
        <div className="space-y-2" style={{ pointerEvents: 'auto' }}>
          {selectedCities.length > 0 && (
            <Button
              onClick={handleNext}
              size="lg"
              variant="default"
              className="w-full"
              aria-label="Ga verder"
            >
              Ga verder
            </Button>
          )}
          <Button
            onClick={handleSkip}
            size="lg"
            variant="link"
            className="w-full"
            aria-label="Sla over"
          >
            Sla over
          </Button>
        </div>
      </div>
    </div>
  );
}


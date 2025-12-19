// Frontend/src/components/news/NewsCountrySelector.tsx
import { cn } from "@/lib/ui/cn";

export interface NewsCountrySelectorProps {
  value: "nl" | "tr";
  onChange: (country: "nl" | "tr") => void;
  className?: string;
}

export function NewsCountrySelector({
  value,
  onChange,
  className,
}: NewsCountrySelectorProps) {
  return (
    <div
      className={cn(
        "flex gap-2 overflow-x-auto px-4 py-2",
        className
      )}
      style={{
        scrollbarWidth: "none", // Firefox
        msOverflowStyle: "none", // IE/Edge
      }}
    >
      {(["nl", "tr"] as const).map((country) => {
        const isActive = value === country;
        return (
          <button
            key={country}
            type="button"
            onClick={() => {
              if (value !== country) {
                onChange(country);
              }
            }}
            className={cn(
              "flex-shrink-0 rounded-sm px-4 py-1.5 text-sm font-gilroy font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2",
              isActive
                ? "bg-primary text-primary-foreground shadow-soft"
                : "bg-gray-100 text-black hover:bg-gray-200"
            )}
            aria-pressed={isActive}
            aria-label={`Select ${country === "nl" ? "Nederland" : "Turkije"}`}
          >
            {country === "nl" ? "Nederland" : "Turkije"}
          </button>
        );
      })}
    </div>
  );
}




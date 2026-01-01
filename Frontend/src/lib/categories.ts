// Frontend/src/lib/categories.ts
import type { SupportedLang } from "@/i18n";
import { nl } from "@/i18n/translations/nl";
import { tr } from "@/i18n/translations/tr";

const translations = {
  nl,
  tr,
} as const;

const CATEGORY_KEY_MAP: Record<string, keyof typeof nl.categories> = {
  restaurant: "restaurant",
  bakery: "bakery",
  supermarket: "supermarket",
  barber: "barber",
  mosque: "mosque",
  travel_agency: "travelAgency",
  butcher: "butcher",
  fast_food: "fastFood",
  cafe: "cafe",
  automotive: "automotive",
  insurance: "insurance",
  tailor: "tailor",
  events_venue: "eventsVenue",
  community_centre: "communityCentre",
  clinic: "clinic",
};

export function humanizeCategoryLabel(input: string | undefined | null): string {
  if (!input) return "—";

  let s = input as string;

  // Replace "_" and "/" with spaces (global)
  s = s.replace(/[_/]/g, " ");

  // Collapse multiple spaces and trim
  s = s.replace(/\s+/g, " ").trim();

  // Capitalize each word
  s = s
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");

  return s;
}

/**
 * Get translated category label
 */
export function getCategoryLabel(categoryKey: string | null | undefined, lang: SupportedLang = "nl"): string {
  if (!categoryKey) return "—";
  
  const normalized = categoryKey.toLowerCase().trim();
  const translationKey = CATEGORY_KEY_MAP[normalized];
  
  if (translationKey && translations[lang]?.categories?.[translationKey]) {
    return translations[lang].categories[translationKey];
  }
  
  // Fallback to humanized version
  return humanizeCategoryLabel(categoryKey);
}



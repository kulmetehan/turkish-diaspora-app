import { describe, expect, it } from "vitest";

import type { LocationMarker } from "@/api/fetchLocations";
import { getCategoryIconIdForLocation, ICON_BASE_ID, FALLBACK_KEY } from "@/lib/map/categoryIcons";

const makeLocation = (overrides: Partial<LocationMarker>): LocationMarker => ({
  id: "loc-1",
  name: "Sample",
  lat: 0,
  lng: 0,
  category: "other",
  state: "VERIFIED",
  rating: null,
  confidence_score: 0.9,
  is_turkish: true,
  ...overrides,
});

describe("getCategoryIconIdForLocation", () => {
  it("returns restaurant marker id for restaurant category", () => {
    const location = makeLocation({ category: "restaurant" });
    expect(getCategoryIconIdForLocation(location)).toBe(`${ICON_BASE_ID}-restaurant`);
  });

  it("returns supermarket marker id when category_key is available", () => {
    const location = makeLocation({ category: "shop", category_key: "supermarket" });
    expect(getCategoryIconIdForLocation(location)).toBe(`${ICON_BASE_ID}-supermarket`);
  });

  it("falls back to other marker id for unknown categories", () => {
    const location = makeLocation({ category: "unknown" });
    expect(getCategoryIconIdForLocation(location)).toBe(`${ICON_BASE_ID}-${FALLBACK_KEY}`);
  });
});


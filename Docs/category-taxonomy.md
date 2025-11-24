# Category Taxonomy & Expansion Guide

This document describes where categories are defined and used throughout the Turkish Diaspora App, and provides a checklist for adding new categories.

## Category Definition Locations

### Backend Configuration

1. **`Infra/config/categories.yml`** - Primary source of truth
   - Defines category metadata: `label`, `description`, `osm_tags`, `aliases`
   - Controls discovery: `discovery.enabled`, `discovery.priority`
   - OSM tags are used by `discovery_bot` to query Overpass API
   - Turkish/Dutch aliases help AI classification recognize category names

2. **`Backend/app/models/categories.py`** - Category enum
   - `Category` enum contains all canonical category keys
   - Used for type safety and validation throughout backend
   - Auto-loaded from `categories.yml` via `CategoryMetadata` class

3. **`Backend/services/prompts/classify_system.txt`** - AI prompt enumeration
   - Lists allowed categories in the system prompt
   - AI model must see the category in the prompt to use it
   - Example: `{"bakery","restaurant","supermarket","barber","butcher","mosque","travel_agency","fast_food","cafe","car_dealer","insurance","tailor"}`

4. **`Backend/app/workers/classify_bot.py`** - Category normalization map
   - `CATEGORY_NORMALIZATION_MAP` maps raw AI outputs to canonical categories
   - Includes Turkish aliases (e.g., "kasap" → "butcher", "berber" → "barber")
   - Ensures consistent category assignment regardless of AI output format

### Discovery Layer

5. **`Backend/app/workers/discovery_bot.py`** - OSM discovery
   - Reads `categories.yml` at runtime
   - Uses `osm_tags` to build Overpass API queries
   - Only processes categories with `discovery.enabled = true`
   - If `osm_tags` are missing or invalid, category is skipped

### Frontend

6. **`Frontend/src/components/Filters.tsx`** - Category filter chips
   - `FALLBACK_CATEGORIES` array includes all categories
   - Categories loaded from API via `categoryOptions` prop
   - Fallback ensures UI works if API fails

7. **`Frontend/src/components/search/CategoryChips.tsx`** - Category chip icons
   - `CATEGORY_ICON_MAP` maps category keys to Lucide icon component names
   - Used for displaying category chips in search/filter UI
   - Missing categories fall back to "Store" icon

8. **`Frontend/src/lib/map/categoryIcons.ts`** - Map marker icon config
   - `RAW_CATEGORY_CONFIG` defines map marker icons
   - Maps category keys to Lucide icon names (kebab-case)
   - Used to generate SVG icons for Mapbox markers

9. **`Frontend/src/lib/map/marker-icons.tsx`** - Marker icon component
   - `getCategoryIcon()` function maps category keys to Lucide icon components
   - Used for rendering category icons in marker components
   - Missing categories fall back to `MapPin`

## Category Expansion Checklist

To fully add a new category (e.g., `car_dealer`, `insurance`, `tailor`), you must update:

### Backend

- [ ] **`Infra/config/categories.yml`**
  - Add category entry with `label`, `description`
  - Define `osm_tags` (use `any` for OR logic, `all` for AND logic)
  - Add Turkish/Dutch `aliases` if applicable
  - Set `discovery.enabled: true/false`
  - Set `discovery.priority: int` (higher = more important)

- [ ] **`Backend/app/models/categories.py`**
  - Add to `Category` enum (e.g., `car_dealer = "car_dealer"`)
  - Enum auto-loads from YAML, but explicit enum ensures type safety

- [ ] **`Backend/services/prompts/classify_system.txt`**
  - Add category to allowed list in system prompt
  - Update description if needed

- [ ] **`Backend/app/workers/classify_bot.py`**
  - Add to `CATEGORY_NORMALIZATION_MAP`
  - Include Turkish aliases if applicable
  - Example: `"oto galeri": "car_dealer"`, `"sigorta": "insurance"`, `"terzi": "tailor"`

### Discovery

- [ ] **OSM tag verification**
  - Test discovery with: `python -m app.workers.discovery_bot --categories <new_category> --limit 5`
  - Verify tags return results in target cities
  - Consider fallback tags if primary tags are sparse

### Frontend

- [ ] **`Frontend/src/components/Filters.tsx`**
  - Add to `FALLBACK_CATEGORIES` array

- [ ] **`Frontend/src/components/search/CategoryChips.tsx`**
  - Add to `CATEGORY_ICON_MAP` with appropriate Lucide icon name
  - Ensure icon is available in lucide-react

- [ ] **`Frontend/src/lib/map/categoryIcons.ts`**
  - Add to `RAW_CATEGORY_CONFIG` with Lucide icon name (kebab-case)
  - Follow existing naming style

- [ ] **`Frontend/src/lib/map/marker-icons.tsx`**
  - Import icon component from lucide-react
  - Add case to `getCategoryIcon()` switch statement

## Example: New Categories (car_dealer, insurance, tailor)

These categories were added following the checklist above:

### Backend ✅
- All three categories defined in `categories.yml` with OSM tags
- All three in `Category` enum
- All three listed in AI prompt
- All three in normalization map with Turkish aliases

### Discovery ✅
- OSM tags defined and tested
- Discovery enabled for all three

### Frontend ✅
- Added to `CATEGORY_ICON_MAP`: `car_dealer: "CarFront"`, `insurance: "ShieldCheck"`, `tailor: "Needle"`
- Added to `RAW_CATEGORY_CONFIG`: `car_dealer: "car-front"`, `insurance: "shield-check"`, `tailor: "needle"`
- Added to `getCategoryIcon()`: cases for all three with imported Lucide components

## Notes

- Categories must be consistent across all layers to avoid UI mismatches
- Missing frontend icons will fall back to generic icons ("Store" for chips, "MapPin" for markers)
- OSM tags must match real OSM data structure; test discovery before production use
- Turkish aliases improve AI classification accuracy for Turkish business names
- The `car_dealer` category now covers a broader automotive set (dealers, garages, car wash/detailing, APK/inspection stations, tyre + car parts shops, motorcycle dealers) via the expanded OSM tag list in `categories.yml`.


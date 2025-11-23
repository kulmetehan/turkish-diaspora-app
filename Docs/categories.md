---
title: Category Management
status: active
last_updated: 2025-01-XX
scope: backend, frontend, discovery
owners: [tda-core]
---

# Category Management

This document explains how categories are managed across the Turkish Diaspora App, from discovery to AI classification to UI display.

## Architecture Overview

Categories flow through three layers:

1. **Configuration** (`Infra/config/categories.yml`) - Source of truth for category definitions
2. **Backend Registry** (`Backend/app/models/categories.py`) - Centralized Category enum and metadata loader
3. **Frontend** (`Frontend/src/api/fetchLocations.ts`) - Dynamic category loading from API

## Category Registry

The central category registry is defined in `Backend/app/models/categories.py`:

- **Category Enum**: Canonical category keys (e.g., `bakery`, `restaurant`, `car_dealer`)
- **CategoryMetadata**: Loads metadata from `categories.yml` at runtime
- **Functions**:
  - `get_all_categories()` - Returns all categories, sorted by priority
  - `get_discoverable_categories()` - Returns only categories with `discovery.enabled: true`
  - `get_category_metadata(key)` - Get metadata for a specific category

## Adding a New Category

To add a new category end-to-end, follow these steps:

### 1. Add to `categories.yml`

Edit `Infra/config/categories.yml` and add a new entry:

```yaml
new_category:
  label: "Human-readable label"
  description: "Description of the category"
  google_types:
    - "google_type_name"  # Optional, legacy
  osm_tags:
    any:
      - { shop: "shop_type" }
      - { amenity: "amenity_type" }
  aliases:
    - "dutch_alias"
    - "turkish_alias"  # TR
  discovery:
    enabled: true
    priority: 5  # Higher = more important
```

### 2. Update Category Enum

Edit `Backend/app/models/categories.py` and add the new category to the `Category` enum:

```python
class Category(str, Enum):
    # ... existing categories ...
    new_category = "new_category"
```

### 3. Update AI Normalization

Edit `Backend/app/workers/classify_bot.py` and add aliases to `CATEGORY_NORMALIZATION_MAP`:

```python
CATEGORY_NORMALIZATION_MAP = {
    # ... existing mappings ...
    "dutch_alias": "new_category",
    "turkish_alias": "new_category",
}
```

### 4. Update AI Prompts

Edit `Backend/services/prompts/classify_system.txt` and:
- Add the new category to the allowed list (line 16)
- Optionally add category-specific rules or examples

### 5. Frontend (Automatic)

The frontend automatically loads categories from the API endpoint (`/api/v1/categories`), so no code changes are needed. The new category will appear in filter chips once the backend is updated.

### 6. Icons (Optional)

If using a category icon system, add an icon mapping for the new category. See `Docs/icon-system.md` for details.

## Category Flow

```
categories.yml
    ↓
Category Enum (models/categories.py)
    ↓
├─→ Discovery Bot (uses osm_tags for OSM queries)
├─→ AI Classification (uses aliases for normalization)
└─→ API Endpoint (/api/v1/categories)
        ↓
    Frontend (dynamic loading)
```

## API Endpoint

**GET `/api/v1/categories`**

Returns a list of all categories with metadata:

```json
[
  {
    "key": "bakery",
    "label": "bakkerij",
    "description": "Bakkerij en bakkerswinkels...",
    "aliases": ["bakker", "turkse bakker", "firin"],
    "google_types": ["bakery"],
    "osm_tags": { "any": [{ "shop": "bakery" }] },
    "is_discoverable": true,
    "discovery_priority": 10
  }
]
```

Query parameters:
- `discoverable_only=true` - Return only categories with `discovery.enabled: true`

## Current Categories

- `bakery` - Bakkerij
- `restaurant` - Restaurant
- `supermarket` - Supermarkt
- `barber` - Kapper
- `mosque` - Moskee
- `travel_agency` - Reisbureau
- `butcher` - Slagerij
- `fast_food` - Fastfood
- `cafe` - Café
- `car_dealer` - Autodealer
- `insurance` - Verzekering
- `tailor` - Kleermaker

## Validation

After adding a new category:

1. **Test discovery**: Run discovery bot for the new category to verify OSM tags work
2. **Test AI**: Classify a test location with the new category to verify normalization
3. **Test frontend**: Verify the category appears in filter chips and can be selected

## Troubleshooting

**Category not appearing in frontend:**
- Check that the category is in the Category enum
- Verify the API endpoint returns the category
- Check browser console for API errors

**AI not recognizing category:**
- Verify aliases are in `CATEGORY_NORMALIZATION_MAP`
- Check that the prompt includes the category in the allowed list

**Discovery not finding locations:**
- Verify `osm_tags` are correct for Netherlands OSM data
- Check that `discovery.enabled: true` is set
- Test OSM query manually using Overpass API






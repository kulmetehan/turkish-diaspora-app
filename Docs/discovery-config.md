---
title: Discovery Category Config
status: active
last_updated: 2025-11-04
scope: backend
owners: [tda-core]
---

# Discovery Category Config

Explains how `Infra/config/categories.yml` maps Turkish diaspora categories to OSM tags, aliases, and discovery parameters used by `discovery_bot`.

## File structure (`Infra/config/categories.yml`)

```yaml
defaults:
  language: "nl"
  region: "NL"
  discovery:
    nearby_radius_m: 1000
    max_per_cell_per_category: 20

categories:
  bakery:
    label: "bakkerij"
    description: "Bakkerij en bakkerswinkels..."
    osm_tags:
      any:
        - { shop: "bakery" }
    aliases:
      - "bakker"
      - "turkse bakker"
    discovery:
      enabled: true
      priority: 10
  ...
```

### Key fields

- `label`, `description`: Human friendly metadata used in admin UI.
- `osm_tags`: Primary driver for OSM Overpass filters. Use `any` / `all` blocks with key/value pairs.
- `aliases`: Turkish/Dutch keywords feeding AI classification heuristics.
- `discovery.enabled`: Toggle category participation. `priority` controls ordering when slicing workloads.
- `google_types`: Legacy field kept for historical parity; currently unused by OSM discovery but retained for potential future dual-provider strategies.

## Lifecycle

1. `discovery_bot` loads `Infra/config/categories.yml` at runtime.
2. For each category with `discovery.enabled = true`, the bot builds OSM queries using the `osm_tags` definition.
3. The category label is stored in `locations.category` and flows through classification/verification.
4. Aliases help the AI layer interpret Turkish phrases when the raw OSM tags are sparse.

### Automotive coverage

- The `automotive` category's `osm_tags.any` list now includes not only car/garage shops but also `amenity=car_wash`, `amenity=vehicle_inspection`, `craft=car_repair`, `shop=tyres`, `shop=car_parts`, and `shop=motorcycle`, ensuring carwash/detailing, APK stations, tyre + parts stores, and motorcycle dealers are all ingested under the existing automotive bucket.

## Catch-all discovery en de `other` categorie

### Doel van de `other` categorie

- `other` is een expliciete catch-all categorie op config-niveau.
- Deze categorie vangt locaties op die:
  - niet in de bestaande categorie-mapping vallen, of
  - niche / minder courante OSM-tags gebruiken.

### Huidige status (actief)

- `other` is nu actief in discovery:
  - `discovery.enabled=true`
  - `discovery.strategy="catch_all"`
  - `discovery.priority=1` (lage prioriteit, draait na specifieke categorieën)
  - `discovery.max_per_cell=10` (conservatieve limiet, lager dan standaard 20)

### Catch-all gedrag

- Per grid/cell wordt een fallback Overpass-query uitgevoerd via `OsmPlacesService`:
  - De query gebruikt key-only filters (`["amenity"]`, `["shop"]`, `["office"]`) via de bestaande fallback-logica in de OSM service.
  - Dit gebeurt door `category_osm_tags=[]` (lege lijst) door te geven, wat de fallback activeert.
- Alle gevonden locaties worden als CANDIDATE met `category="other"` opgeslagen.
- Specifieke categorieën blijven via hun eigen `osm_tags` draaien (ongewijzigd).
- Deduplicatie (via `place_id` + fuzzy match) voorkomt dubbele entries als een locatie ook al via een specifieke categorie is gevonden.

### Placeholder `osm_tags`

- `other` heeft een `osm_tags.any` met een placeholder entry:
  - Dit is uitsluitend om de bestaande validator (`Backend/scripts/validate_osm_mapping.py`) tevreden te houden.
  - Deze tags worden **niet gebruikt** in Overpass queries voor catch-all discovery.
  - De catch-all branch in `discovery_bot.py` detecteert `strategy="catch_all"` en gebruikt de fallback-logica in plaats van deze placeholder tags.

### Beperkingen / limieten

- Catch-all gebruikt bewust een lagere `max_per_cell` (10 vs 20) om Overpass-load te beperken.
- Er is al een circuit breaker en rate limiting in de discovery pipeline:
  - Circuit breaker: stopt bij te veel opeenvolgende fouten of hoge error ratio
  - Rate limiting: per-endpoint semaphore + minimum delay tussen requests
- Catch-all draait met lage prioriteit (1), zodat specifieke categorieën eerst worden verwerkt.

### Frontend gedrag

- De frontend toont `other` niet in de publieke categorie-chips:
  - `/api/v1/categories?discoverable_only=true` retourneert `other` (omdat `discovery.enabled=true`),
  - maar de frontend filtert de sleutel `"other"` expliciet uit de categorie-lijst (`Frontend/src/api/fetchLocations.ts`).
- Locaties met `category="other"` zijn wel zichtbaar op de kaart als ze VERIFIED zijn (via de normale visibility rules).

### Scope van deze implementatie

- Dit is een eerste, minimale activatie van Catch-All Discovery.
- Verdere tuning (extra filters, exclusion van features die al onder specifieke categories vallen, metrics, etc.) komt in vervolg-stories.

## Validation tips

- Run `python -m app.workers.discovery_bot --categories <cat> --limit 5 --dry-run` after editing the YAML to ensure queries still return results.
- Use `yamllint` or `python - <<'PY'` with `yaml.safe_load` to confirm the file parses.
- Maintain a short comment history in the YAML when adjusting priorities or aliases.

## Related configs

- `Infra/config/cities.yml` — grid definitions, bounding boxes, district metadata.
- `Docs/city-grid.md` — documentation for city grid strategy.
- `Docs/osm-discovery-improvements.md` — production hardening notes for the discovery pipeline.

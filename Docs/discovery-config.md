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

## Validation tips

- Run `python -m app.workers.discovery_bot --categories <cat> --limit 5 --dry-run` after editing the YAML to ensure queries still return results.
- Use `yamllint` or `python - <<'PY'` with `yaml.safe_load` to confirm the file parses.
- Maintain a short comment history in the YAML when adjusting priorities or aliases.

## Related configs

- `Infra/config/cities.yml` — grid definitions, bounding boxes, district metadata.
- `Docs/city-grid.md` — documentation for city grid strategy.
- `Docs/osm-discovery-improvements.md` — production hardening notes for the discovery pipeline.

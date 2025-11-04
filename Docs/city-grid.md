---
title: City Grid Definitions (Rotterdam)
status: active
last_updated: 2025-11-04
scope: data-ops
owners: [tda-core]
---

# City Grid Definitions

Describes how `Infra/config/cities.yml` encodes discovery grids for Rotterdam (and future cities) and how `discovery_bot` consumes them.

## YAML structure (`Infra/config/cities.yml`)

```yaml
rotterdam:
  bbox:
    lat_min: 51.85
    lat_max: 51.98
    lng_min: 4.35
    lng_max: 4.55
  districts:
    centrum:
      center: [51.9225, 4.4792]
      grid_span_km: 4.0
      cell_spacing_m: 800
    noord:
      center: [51.945, 4.466]
      grid_span_km: 4.0
      cell_spacing_m: 800
    ...
```

- `bbox`: Master bounding box used by metrics (`metrics_service._rotterdam_progress`).
- `districts`: Named configurations processed by `discovery_bot`. Each district yields grid points based on `center`, `grid_span_km`, and `cell_spacing_m`.
- Additional cities should follow the same structure (`cities.<name>`).

## How discovery uses it

- CLI flag `--city rotterdam --district centrum` (future) will scope to a specific district once filtering is enabled.
- Currently the bot iterates over all districts for the requested city.
- Grid points are subdivided when density exceeds thresholds (`MAX_SUBDIVIDE_DEPTH`).

## Validation

```bash
python -m app.workers.discovery_bot --city rotterdam --categories restaurant --limit 20 --dry-run
```

Check output to ensure each district contributes results and the bbox aligns with expected geography.

## Expansion checklist

1. Define new city entry in `Infra/config/cities.yml` with bbox + districts.
2. Update discovery workflows (`tda_discovery.yml`) to include new `--city` target.
3. Run small dry-run batches before scheduling full automation.
4. Update metrics snapshot to include new city-specific KPIs if desired.

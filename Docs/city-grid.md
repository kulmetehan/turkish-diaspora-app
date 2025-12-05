---
title: City Grid Definitions (Rotterdam)
status: active
last_updated: 2025-11-04
scope: data-ops
owners: [tda-core]
---

# City Grid Definitions

Describes how `Infra/config/cities.yml` encodes discovery grids for Rotterdam (and future cities) and how `discovery_bot` consumes them. Cities and districts can be managed via the admin UI (`#/admin/cities`) or through manual YAML editing.

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

## Admin UI Management

Cities and districts can be managed through the admin interface at `#/admin/cities`, which provides a user-friendly way to add, edit, and delete cities and districts without manually editing YAML files.

### Features

- **Full CRUD operations**: Create, read, update, and delete cities and districts
- **Automatic validation**: Coordinates are validated (6 decimal precision) and must be within valid WGS84 ranges
- **Automatic bounding box calculation**: When adding districts, bounding boxes are automatically calculated from center coordinates (±0.015 degrees)
- **Direct YAML writing**: Changes are written directly to `Infra/config/cities.yml` with automatic backups
- **District management**: View all districts for each city in an expandable section with edit/delete functionality
- **Coordinate precision**: Input fields support 6 decimal precision for accurate coordinate entry

### Usage

1. Navigate to the Cities page in the admin interface (`#/admin/cities`)
2. Click "Add City" to create a new city with center coordinates
3. Use "Add District" on any city card to add districts
4. Click "Expand Districts" to view, edit, or delete existing districts
5. All changes are automatically saved with backup files created before each write

For authentication requirements, see [`Docs/admin-auth.md`](./admin-auth.md).

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

1. Add city entry via Admin UI (`#/admin/cities`) or manually edit `Infra/config/cities.yml` with city center coordinates and districts.
2. Update discovery workflows (`tda_discovery.yml`) to include new `--city` target.
3. Run small dry-run batches before scheduling full automation.
4. Update metrics snapshot to include new city-specific KPIs if desired.

Note: Using the Admin UI is recommended as it automatically validates coordinates, calculates bounding boxes, and creates backups of the configuration file.

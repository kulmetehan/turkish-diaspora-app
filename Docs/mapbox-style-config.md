---
title: Mapbox Style Configuration
status: active
last_updated: 2025-01-XX
scope: frontend
owners: [tda-frontend]
---

# Mapbox Style Configuration

Guide to configuring and managing Mapbox styles for the Turkish Diaspora App maps.

## Current Configuration

**Style URL**: `mapbox://styles/mapbox/standard` (Mapbox Standard style)

**Used for**: All maps (public location map and Admin Discovery Coverage map)

**Configuration location**: `Frontend/src/lib/config.ts` → `CONFIG.MAPBOX_STYLE`

**Environment override**: `VITE_MAPBOX_STYLE` (optional)

## How It Works

The Mapbox style is set once during map initialization via `initMap()` in `Frontend/src/lib/map/mapbox.ts`. All maps (public and admin) share the same style configuration from `CONFIG.MAPBOX_STYLE`.

### Configuration Flow

```
VITE_MAPBOX_STYLE (env var, optional)
    ↓
CONFIG.MAPBOX_STYLE (config.ts)
    ↓
initMap() → new mapboxgl.Map({ style: CONFIG.MAPBOX_STYLE })
```

## Known Warnings

The Mapbox Standard style (`mapbox://styles/mapbox/standard`) produces some console warnings that are **internal to the style JSON** and cannot be eliminated from our code:

1. **`"featureNamespace place-A of featureset place-labels's selector is not associated to the same source, skip this selector"`**
   - Root cause: Mapbox Standard style JSON references a `place-A` feature namespace that points to a different source than expected
   - Impact: None (warning only, functionality unaffected)

2. **`"Cutoff is currently disabled on terrain"`**
   - Root cause: Style includes terrain-related layers with cutoff expressions, but terrain is disabled in our map configuration
   - Impact: None (warning only, functionality unaffected)

3. **`Failed to evaluate expression ... ["get","sizerank"] ... evaluated to null but was expected to be of type number`**
   - Root cause: Style uses `sizerank` in label sizing expressions, but some vector tile features lack this property
   - Impact: None (warning only, functionality unaffected)

**Important**: These warnings are **not caused by our code**. We do not modify base style layers (place-labels, etc.) or manipulate sizerank expressions. The warnings originate from the Mapbox Standard style JSON itself.

## Changing the Style

### For All Maps

To change the style for all maps (public and admin):

1. Set `VITE_MAPBOX_STYLE` in your environment:
   ```bash
   # In Frontend/.env.development or Frontend/.env.production
   VITE_MAPBOX_STYLE=mapbox://styles/mapbox/streets-v12
   ```

2. Or modify the default in `Frontend/src/lib/config.ts`:
   ```typescript
   MAPBOX_STYLE:
     (import.meta.env.VITE_MAPBOX_STYLE as string | undefined) ??
     "mapbox://styles/mapbox/streets-v12", // Changed default
   ```

### Testing Checklist

After changing the style, verify:

- [ ] Public map renders correctly (markers, clustering, interactions)
- [ ] Admin Discovery Coverage map renders correctly:
  - [ ] Heatmap layer displays
  - [ ] Coverage grid (fill layer) displays
  - [ ] Outline layer displays
  - [ ] "Show coverage" toggle works
  - [ ] Click interactions work (popups)
- [ ] Check browser console for new warnings/errors
- [ ] Verify layer insertion logic still works (AdminDiscoveryMap checks for `waterway-label` which may not exist in all styles)

### Layer Dependencies

**Admin Discovery Coverage Map** (`Frontend/src/components/admin/AdminDiscoveryMap.tsx`):

- Heatmap layer is inserted before `"waterway-label"` if it exists (checked via `safeHasLayer()`)
- If `"waterway-label"` doesn't exist in the new style, the heatmap is appended to the layer stack
- Coverage fill and outline layers are inserted relative to the heatmap layer

**No other layer dependencies**: The public map (MapView) and marker layers do not depend on specific base style layer IDs.

## Style Options

Common Mapbox hosted styles you can use:

- `mapbox://styles/mapbox/standard` (current default)
- `mapbox://styles/mapbox/streets-v12`
- `mapbox://styles/mapbox/light-v11`
- `mapbox://styles/mapbox/dark-v11`
- `mapbox://styles/mapbox/satellite-v9`

**Note**: Different styles may produce different warnings. If you switch styles to avoid warnings, test thoroughly to ensure all map functionality still works.

## Related Documentation

- `Docs/env-config.md` — Environment variable configuration
- `Docs/map-ux-upgrade.md` — Mapbox GL migration overview
- `Frontend/src/lib/config.ts` — Configuration source code
- `Frontend/src/lib/map/mapbox.ts` — Map initialization




























# Frontend Map Icons

The public map now renders category-specific markers instead of generic circles. This document captures how the icon system works and how to extend it safely.

## Where the icons live

- The sprite factory lives in `Frontend/src/lib/map/categoryIcons.ts`.
- Each `CategoryIconSpec` defines the key, palette, and a `draw` function that paints onto a high-DPI canvas.
- `CATEGORY_ICON_BASE_SIZE` is fixed at 48 CSS pixels. The renderer automatically scales up to the current `devicePixelRatio` (minimum 2x, capped at 3x) before registering the image with Mapbox so icons stay crisp on retina displays.

## Registration lifecycle

- `ensureCategoryIcons(map)` runs inside `ensureBaseLayers` and again on every `styledata` event. It skips ids that already exist, so repeated calls are cheap.
- The helper adds one fallback icon (`tda-marker-other`) plus one per known category. All ids follow the pattern `tda-marker-<category-key>`.
- Because icons are bound to the Mapbox style, they must be re-added after each style reload. The `MarkerLayer` effect takes care of this; consumers do not need to call the helper manually.

## Lifecycle & Order

- Attach the `styleimagemissing` fallback listener as soon as the map instance exists (before adding sources or layers).
- Call `ensureCategoryIcons(map)` on `load`, `style.load`, `styledata`, and the first `idle` event so sprites repopulate after every style churn.
- Add the data source and layers in this order: clusters → cluster-count → halo → unclustered symbol (which relies on the icon ids).
- Push GeoJSON data only after confirming the required icon ids are registered; reschedule via `idle` if any sprite is still missing.
- The lazy fallback handler registers any on-demand ids, triggers a repaint, and nudges the symbol layout so icons appear on the next frame.

## GeoJSON contract

- `buildMarkerGeoJSON` attaches two new properties to every feature:
  - `categoryKey`: normalized and lowercase (using `normalizeCategoryKey`) for grouping/debugging.
  - `icon`: the exact sprite id returned by `getCategoryIconIdForLocation`.
- The symbol layer uses `["coalesce", ["get", "icon"], "default-icon"]` to stay resilient if a category lacks an explicit icon.

## Selection styling

- Selection still flows through `feature-state.selected`.
- The symbol layer reacts by:
  - Scaling the icon (`icon-size` 1.12 vs 1).
  - Expanding the halo width and brightness with short paint transitions (120 ms) to give a subtle pulse.
  - Leaving the base colours untouched so each category remains recognizable.

## Adding a new category icon

1. Add a new entry to the `CATEGORY_ICON_SPECS` array.
   - Choose a distinct background/accent colour pair.
   - Implement a `draw(ctx, size)` routine; work in CSS pixels and let the renderer handle DPI scaling.
2. Exported helpers automatically expose the new key:
   - `getCategoryIconId(<key>)` returns `tda-marker-<key>`.
   - `normalizeCategoryKey` will match the new key if the backend returns it via `category_key`.
3. Update tests if necessary (e.g. expectations in `components/__tests__/markerLayer.spec.tsx`).

## Debugging tips

- Use `map.hasImage("tda-marker-<key>")` in the browser console to confirm registration.
- Enable Mapbox's "Show tile boundaries" debug control to verify that halo sizing respects zoom transitions.
- When verifying retina output, zoom the browser window to inspect the canvas; the sprites are rendered off-screen, so `map.listImages()` can also list all registered ids.



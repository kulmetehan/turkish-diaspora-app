# Icon System - Snap-style Marker Design

## Overview

The Turkish Diaspora App uses a compact Snap-style marker system with red badges and white Lucide icons. This document describes the design tokens, implementation, and guidelines for the F4-S2 marker system.

## Design Specification

### Visual Design

- **Base**: Red badge (#EF4444, red-500) with rounded rectangle shape
- **Icons**: White Lucide icons centered within the badge
- **Size**: 32px × 32px (compact, down from previous 48px)
- **Shape**: Rounded rectangle with 8px border radius (pill-like appearance)
- **Icon Size**: 16px Lucide icons within the 32px marker

### Design Tokens

All design tokens are defined in `Frontend/src/lib/map/categoryIcons.ts`:

```typescript
export const MARKER_BASE_SIZE = 32; // Compact size, down from 48px
export const MARKER_FILL_DEFAULT = "#EF4444"; // red-500, Snap-style red
export const MARKER_FILL_SELECTED = "#DC2626"; // red-600, optional for future use
export const MARKER_ICON_COLOR = "#FFFFFF"; // white
export const MARKER_STROKE_COLOR = "rgba(0, 0, 0, 0.1)"; // subtle shadow
export const MARKER_BORDER_RADIUS = 8; // pill/rounded rect shape
export const MARKER_ICON_PADDING = 6; // inner padding for Lucide glyph
export const MARKER_ICON_SIZE = 16; // Lucide icon size within marker
```

### Selected State

When a marker is selected:

- **Halo**: 14px radius circle with 40% opacity, blue (#0ea5e9) with white stroke (1.5px)
- **Icon Scale**: Optional 8% scale increase (1.08) - removed if blur occurs on high-DPR screens
- **Icon Opacity**: 100% (vs 82% for unselected)

## Category Mapping

The system supports 8 categories, each mapped to a Lucide icon:

| Category Key | Lucide Icon | Description |
|-------------|-------------|-------------|
| `restaurant` | `Utensils` | Restaurants and eateries |
| `supermarket` | `ShoppingCart` | Supermarkets and grocery stores |
| `bakery` | `Croissant` | Bakeries |
| `butcher` | `Beef` | Butcher shops |
| `barber` | `Scissors` | Barbershops and hair salons |
| `cafe` | `Coffee` | Cafes |
| `mosque` | `Building2` | Mosques |
| `other` | `MapPin` | Fallback/default category |

## Retina / High-DPR Handling

The icon system automatically handles high-DPI displays:

- **Base Size**: 32 CSS pixels
- **DPR Clamping**: Device pixel ratio is clamped to 1-3x and rounded
- **Rendering**: SVGs are rendered to canvas at `size × DPR`, then converted to ImageBitmap
- **Registration**: Icons are registered with Mapbox using `pixelRatio` option for crisp rendering

Example: On a 2x Retina display, a 32px icon is rendered as 64px bitmap, then registered with `pixelRatio: 2`.

## Rendering Locations

### Map Markers

**Location**: `Frontend/src/lib/map/categoryIcons.ts`

- SVGs are generated at runtime using `buildMarkerSvg()`
- Rounded rectangle shape with red background and white Lucide icon
- SVGs are rendered to canvas, converted to ImageBitmap, and registered with Mapbox via `map.addImage()`
- Icons are used in Mapbox symbol layers (`tda-unclustered-point`)

**Layer Configuration**:
- Uses `icon-image` property with feature-state-driven `icon-size` for selection
- `icon-allow-overlap: true` and `icon-ignore-placement: true` for performance

### List Icons

**Location**: `Frontend/src/lib/map/marker-icons.tsx`

- React component (`MarkerIcon`) renders category-based icons
- Uses same design tokens as map markers for visual consistency
- Renders red badge with white Lucide icon matching map design
- Supports selected state with ring and scale styling

## Implementation Details

### SVG Generation

The `buildMarkerSvg()` function generates Snap-style markers:

1. Builds Lucide icon SVG (24×24 viewBox)
2. Creates rounded rectangle background (32×32 with 8px radius)
3. Centers and scales icon to 16px within the marker
4. Applies white stroke color and proper transforms
5. Uses integer-based viewBox (0 0 32 32) to avoid sub-pixel blurring

### Icon Registration

Icons are registered per map instance:

- Cached by map instance and DPR to prevent duplicate registration
- Re-registered on `styledata` events (style changes)
- Fallback handler (`styleimagemissing`) registers missing icons on-demand
- All icons use the same 32px base size

### Fallback Behavior

If an icon is missing or a new category is encountered:

- `styleimagemissing` event handler registers the fallback icon (`tda-marker-v2-other`)
- Fallback uses the same Snap-style design (red badge with map-pin icon)
- Registration is non-blocking and triggers a repaint

## Adding New Categories

To add a new category icon:

1. **Add to category config** in `categoryIcons.ts`:
   ```typescript
   const RAW_CATEGORY_CONFIG = [
     // ... existing categories
     { key: "new_category", lucide: "IconName" },
   ];
   ```

2. **Update list icon mapping** in `marker-icons.tsx`:
   ```typescript
   function getCategoryIcon(categoryKey: string | null | undefined): LucideIcon {
     switch (normalized) {
       // ... existing cases
       case "new_category":
         return IconName;
     }
   }
   ```

3. **Choose appropriate Lucide icon**:
   - Must be white on red background
   - Should be recognizable at 16px size
   - Keep within 32px base size constraint

4. **Test**:
   - Verify icon appears correctly on map
   - Check list view consistency
   - Test on high-DPR displays

## Constraints & Guidelines

- **Icon Size**: Must fit within 32px base size
- **Color**: Icons must be white (`#FFFFFF`) on red background
- **Shape**: Rounded rectangle (8px radius) for consistency
- **DPR**: Supports 1x, 2x, and 3x displays (clamped and rounded)
- **Performance**: Icons are cached per map instance and DPR

## Cross-References

- **Technical Implementation**: See `Docs/frontend-map-icons.md` for Mapbox layer setup and lifecycle details
- **Category Configuration**: See `Infra/config/categories.yml` for backend category definitions
- **Source Code**: 
  - `Frontend/src/lib/map/categoryIcons.ts` - Map icon generation and registration
  - `Frontend/src/components/markerLayerUtils.ts` - Mapbox layer configuration
  - `Frontend/src/lib/map/marker-icons.tsx` - List icon component

## Version History

- **F4-S2**: Snap-style design implemented (32px compact markers, red badges, white icons)
- **v2**: Previous version with 48px circular markers





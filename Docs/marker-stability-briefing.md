# Briefing: Fix Check-In Marker Stability Issue

## Problem Statement

Check-in markers (user avatars) on the map are **unstable during zoom operations**. While geographic coordinates remain correct, the screen positions of HTML markers drift relative to the map during zoom/pan, making them appear to "float" or move incorrectly. This is inconsistent with location markers, which remain perfectly stable.

**User Report:**
> "De markers zouden stabiel op hun plek moeten blijven. Dit geldt niet voor alle markers overigens. Zo is er de marker voor locatie Beydagi vatan bakkerij, die staat zeer centraal op de kaart vanaf eerste load en veranderd nooit."

**Key Observation:** Location markers (which use Mapbox symbol layers) are stable, while check-in markers (which use HTML markers) are not.

## Root Cause Analysis

**Confirmed via Debug Logs:**
- Geographic coordinates (`lng`, `lat`) are **stable** (`lngDiff: 0`, `latDiff: 0`)
- Screen positions (`markerRect.x`, `markerRect.y`) **change significantly** during zoom
- Example: Location 306 marker moved from `{x: 665, y: 311}` to `{x: 663.44, y: 278.88}` during zoom

**Technical Root Cause:**
- **HTML markers** (`mapboxgl.Marker`) are DOM elements positioned by Mapbox GL
- During zoom, Mapbox GL recalculates screen positions, but DOM updates can lag or be inconsistent
- This is a **fundamental limitation** of HTML markers in Mapbox GL JS
- **Solution:** Switch to Mapbox **symbol layers** (like location markers) for stable, GPU-accelerated rendering

## Current Implementation

**File:** `Frontend/src/components/UserCheckInLayer.tsx`

**Current Approach:**
- Uses `mapboxgl.Marker` (HTML markers) for individual check-in avatars
- Creates DOM elements via `createMarkerElement()` and `createAvatarElement()`
- Handles multiple users per location with overlapping avatars
- Supports avatar images (`avatar_url`) and fallback initials

**Key Functions:**
- `createAvatarElement(user, size)` - Creates individual avatar DOM element
- `createMarkerElement(users, userCount)` - Creates container with multiple avatars
- Marker creation happens in `useEffect` at lines 565-645

**Reference Implementation (Stable Markers):**
- `Frontend/src/components/MarkerLayer.tsx` - Uses symbol layers for location markers
- `Frontend/src/components/markerLayerUtils.ts` - Layer creation utilities
- `Frontend/src/lib/map/categoryIcons.ts` - Icon registration system

## Solution Requirements

### 1. Switch to Mapbox Symbol Layers

Replace HTML markers with Mapbox symbol layers for stable positioning:

**Required Changes:**
1. **Register avatar images** with `map.addImage()` before use
2. **Create symbol layer** (`type: "symbol"`) for individual check-ins
3. **Handle multiple users** per location (options below)
4. **Support fallbacks** for missing avatars (initials)

### 2. Avatar Image Registration

**Pattern to Follow:** See `Frontend/src/lib/map/categoryIcons.ts`:
- `registerIconIfMissing()` - Registers SVG-based icons
- `ensureCategoryIcons()` - Ensures all icons are registered
- Uses `renderSvgToCanvas()` and `toBitmap()` for conversion

**For Avatars:**
- Load avatar images from URLs (`user.avatar_url`)
- Convert to `ImageBitmap` or `HTMLImageElement`
- Register with `map.addImage(imageId, image, { pixelRatio: dpr })`
- Handle async loading and errors gracefully

### 3. Multiple Users Per Location

**Options:**

**Option A: Single Feature with First User's Avatar**
- Use first user's avatar as icon
- Show count badge via `text-field` property
- Simpler, but less visual detail

**Option B: Multiple Features (One Per User)**
- Create separate GeoJSON feature for each user
- Each feature gets its own avatar icon
- More complex, but shows all users

**Option C: Sprite Sheet**
- Generate composite image with multiple avatars
- More complex, requires sprite generation

**Recommendation:** Start with **Option A** (simpler), can enhance later.

### 4. Fallback for Missing Avatars

**Current:** Uses initials in gradient background (`getInitials()`)

**For Symbol Layers:**
- Generate SVG with initials and gradient background
- Register as image (similar to category icons)
- Use `coalesce` expression to fallback: `["coalesce", ["image", ["get", "avatar"]], ["image", "tda-checkin-fallback"]]`

## Implementation Steps

### Step 1: Avatar Image Registration System

Create functions to:
1. Load avatar image from URL
2. Convert to ImageBitmap
3. Register with Mapbox map
4. Handle errors and fallbacks
5. Track registered images (avoid duplicates)

**Reference:** `Frontend/src/lib/map/categoryIcons.ts` - `registerIconIfMissing()`

### Step 2: Update GeoJSON Builder

Modify `buildCheckInGeoJSON()` to include:
- `icon` property with avatar image ID
- `user_count` property (already exists)
- `avatar_url` property for reference

**Example:**
```typescript
properties: {
  id: `checkin-${item.location_id}`,
  location_id: item.location_id,
  user_count: item.count || item.users.length,
  icon: `tda-checkin-avatar-${item.users[0]?.id || 'fallback'}`,
  avatar_url: item.users[0]?.avatar_url || null,
}
```

### Step 3: Create Symbol Layer

Add symbol layer similar to `L_POINT` in `markerLayerUtils.ts`:

```typescript
map.addLayer({
  id: L_POINT,
  type: "symbol",
  source: SRC_ID,
  filter: ["!", ["has", "point_count"]], // Only non-clustered points
  layout: {
    "icon-image": [
      "coalesce",
      ["image", ["get", "icon"]],
      ["image", "tda-checkin-fallback"]
    ],
    "icon-size": 1.0,
    "icon-allow-overlap": true,
    "icon-ignore-placement": true,
  },
  paint: {
    "icon-opacity": 1.0,
  },
});
```

### Step 4: Remove HTML Markers

Remove the `useEffect` that creates HTML markers (lines 565-645) and replace with:
- Avatar image registration logic
- Symbol layer creation
- Click handlers on symbol layer (use `map.on("click", L_POINT, ...)`)

### Step 5: Handle Click Events

Replace HTML marker click handlers with Mapbox layer click handler:

```typescript
map.on("click", L_POINT, (e) => {
  const features = map.queryRenderedFeatures(e.point, { layers: [L_POINT] });
  if (!features.length) return;
  const feature = features[0];
  const locationId = feature.properties.location_id;
  // Show popup with user list
});
```

## Technical Constraints

1. **React Strict Mode:** Component mounts twice, ensure idempotent operations
2. **Async Image Loading:** Avatars load asynchronously, handle race conditions
3. **Memory Management:** Track registered images, avoid memory leaks
4. **Error Handling:** Handle failed image loads gracefully
5. **Performance:** Register images efficiently, avoid blocking render

## Success Criteria

✅ **Markers remain stable** during zoom/pan operations
✅ **No visual drift** - markers stay fixed to geographic coordinates
✅ **Avatar images display** correctly (when available)
✅ **Fallback initials** display for missing avatars
✅ **Multiple users** handled appropriately
✅ **Click interactions** work (popup shows user list)
✅ **No console errors** related to image registration
✅ **Performance** - no lag during zoom/pan

## Reference Files

**Primary Files:**
- `Frontend/src/components/UserCheckInLayer.tsx` - Current implementation (needs refactor)
- `Frontend/src/components/MarkerLayer.tsx` - Reference for stable symbol layers
- `Frontend/src/components/markerLayerUtils.ts` - Layer creation utilities
- `Frontend/src/lib/map/categoryIcons.ts` - Icon registration patterns

**Supporting Files:**
- `Frontend/src/lib/api.ts` - CheckInItem, UserCheckIn type definitions
- `Frontend/src/components/MapView.tsx` - Map initialization
- `Docs/frontend-map-icons.md` - Icon system documentation

## Debug Logging

**Current Debug Logs:** Extensive logging already in place (see `UserCheckInLayer.tsx`)
- Hypothesis A: Data flow tracking
- Hypothesis B: GeoJSON building
- Hypothesis C: Layer creation
- Hypothesis D: Marker creation
- Hypothesis E: Sprite registration
- Hypothesis F: Marker position tracking

**Keep logs active** during implementation to verify:
- Avatar image registration
- Symbol layer creation
- Marker stability during zoom

## Notes

- **Cluster layer** already works correctly (uses symbol layers)
- **Sprite registration** for clusters is fixed (uses Set-based tracking)
- **Location markers** are stable (reference implementation)
- Focus on **individual check-in markers** (non-clustered points)

## Questions to Resolve

1. **Multiple users:** Single avatar or multiple features?
2. **Avatar size:** What size should avatar icons be? (Current: 40px for single, 36px for multiple)
3. **Badge display:** How to show user count badge on symbol layer?
4. **Popup positioning:** Use Mapbox Popup or custom solution?

## Next Steps

1. Read and understand current `UserCheckInLayer.tsx` implementation
2. Study `MarkerLayer.tsx` and `markerLayerUtils.ts` for patterns
3. Implement avatar image registration system
4. Create symbol layer for check-ins
5. Remove HTML marker code
6. Test marker stability during zoom/pan
7. Verify all functionality (clicks, popups, multiple users)




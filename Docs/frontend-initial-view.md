# Frontend Initial View & Geolocation Heuristics

**Status**: Active  
**Last Updated**: 2025-01-XX  
**Scope**: Frontend map initialization  
**Owners**: TDA Core Team

## Overview

This document describes the smart initial map centering logic that determines the initial view when the app loads. The system uses geolocation (if permission is already granted) and falls back to Rotterdam, ensuring at least one unclustered marker is visible when data exists.

## Initial Load Sequence

The initial map load follows this sequence:

1. **App mounts** → `HomePage` component renders
2. **MapView mounts** → `useInitialMapCenter` hook initializes
3. **Geolocation/permission check** → Permissions API query (if available)
4. **Initial center/zoom determined** → Either geolocation or Rotterdam fallback
5. **Map instance created** → Mapbox map initialized with initial center/zoom
6. **Map loads** → `mapReady` becomes true
7. **Marker layer ready** → Locations loaded, source available
8. **Unclustered marker heuristic** → Adjusts view to ensure at least one marker visible
9. **Viewport fetch** → First bbox-based fetch (suppressed during initial transitions)

## Geolocation Decision Tree

The system uses the following decision tree to determine the initial center:

```
Is Permissions API supported?
├─ Yes
│  ├─ Query permission state
│  │  ├─ "granted" → Request position
│  │  │  ├─ Success → Check coverage bounds
│  │  │  │  ├─ Within Rotterdam bounds → Use geolocation center
│  │  │  │  └─ Outside bounds → Fallback to Rotterdam
│  │  │  └─ Error/Timeout → Fallback to Rotterdam
│  │  ├─ "denied" → Fallback to Rotterdam (no prompt)
│  │  └─ "prompt" → Fallback to Rotterdam (no auto-prompt)
│  └─ Query fails → Fallback to Rotterdam
└─ No
   └─ Fallback to Rotterdam
```

### Key Behaviors

- **No auto-prompt**: The system never automatically prompts for geolocation permission. It only uses geolocation if permission is already granted.
- **Coverage check**: Even if geolocation succeeds, coordinates are checked against Rotterdam bounds (`51.85 ≤ lat ≤ 51.98`, `4.35 ≤ lng ≤ 4.55`). If outside, falls back to Rotterdam.
- **Timeout**: Geolocation requests have an 8000ms timeout. On timeout, falls back to Rotterdam.
- **Error handling**: All geolocation errors (permission denied, position unavailable, timeout) result in Rotterdam fallback.

## Coverage Fallback

### Rotterdam Bounding Box

The coverage area is defined by:

- **Latitude**: 51.85 to 51.98
- **Longitude**: 4.35 to 4.55

This bbox is based on `Infra/config/cities.yml` and `Docs/city-grid.md` definitions.

### Fallback Logic

When a geolocated position is outside the Rotterdam bounds:

1. The system detects this using `isWithinRotterdamBounds()` from `Frontend/src/lib/geo.ts`
2. Falls back to Rotterdam default center: `[4.4777, 51.9244]` (from `CONFIG.MAP_DEFAULT`)
3. Uses default zoom: `11` (from `CONFIG.MAP_DEFAULT.zoom`)
4. Sets `source: 'fallback_city'` in the initial center result

This ensures users outside the coverage area always see Rotterdam on initial load, providing a consistent experience.

## Unclustered Marker Visibility Heuristic

### Goal

Ensure that when data exists, at least one unclustered marker is visible in the initial view.

### Implementation

The heuristic is implemented in `Frontend/src/lib/initialView.ts` as `computeInitialUnclusteredView()`:

1. **Wait for prerequisites**:
   - Map style loaded (`map.isStyleLoaded()`)
   - Marker source exists and is ready
   - Locations array has data

2. **Find nearest feature**:
   - Uses `querySourceFeatures()` to get all features in the source
   - Calculates distance from initial center to each feature
   - Selects the nearest feature (marker or cluster)

3. **Handle clusters**:
   - If nearest feature is a cluster:
     - Uses `getClusterExpansionZoom(clusterId, callback)` to get zoom where cluster splits
     - Caps zoom at `CLUSTER_CONFIG.MAX_ZOOM` (desktop) or `CLUSTER_CONFIG.MOBILE_MAX_ZOOM` (mobile)
     - Centers on cluster and zooms to expansion level
   - If nearest feature is already a point marker:
     - Uses `MAX_ZOOM - 1` or `MOBILE_MAX_ZOOM - 1` to ensure it stays unclustered
     - Centers on marker

4. **Apply view**:
   - Uses `performCameraTransition()` with 400ms duration
   - Calls `onSuppressNextViewportFetch()` to prevent unnecessary fetch
   - Marks as settled to prevent re-runs

### Cluster Configuration

The heuristic uses cluster config from `Frontend/src/lib/config.ts`:

- **Desktop**: `MAX_ZOOM: 15`, `RADIUS: 30`
- **Mobile**: `MOBILE_MAX_ZOOM: 16`, `RADIUS: 24` (30 * 0.8)

### Empty Dataset

If no features exist, the heuristic returns `null` and the initial city/geolocation zoom is kept. The requirement is "at least one unclustered marker visible **when there is data**".

## Viewport Fetch Interaction

### Suppression Mechanism

To prevent unnecessary fetches during initial camera transitions:

1. **Initial geolocation centering**: When `performCameraTransition()` succeeds for geolocation-based initial center, `onSuppressNextViewportFetch()` is called
2. **Unclustered marker heuristic**: When the heuristic applies a view adjustment, `onSuppressNextViewportFetch()` is called
3. **Cluster expansion**: When expanding clusters (via "locate me" button or cluster click), suppression is used

### Fetch Flow

1. **Global fetch**: Runs on app mount, independent of viewport (no bbox)
2. **Initial viewport fetch**: Triggered after map emits first bbox (after `moveend` event)
3. **Subsequent fetches**: Normal viewport-based fetching with 200ms debounce

### Avoiding Double Fetches

- `lastSettledBboxRef` in `App.tsx` prevents duplicate fetches for the same bbox
- `hasSettledRef` tracks whether initial settle has occurred
- Suppression mechanism prevents fetch during programmatic camera movements

## Camera Cache Behavior

The camera cache (`Frontend/src/components/mapCameraCache.ts`) stores the last known camera state:

- **Restoration**: On map load, if no focus is active, cached camera is restored
- **Geolocation override**: If initial center is from geolocation, cache is cleared to prevent override
- **Storage**: Camera state is stored on component unmount via `storeCamera()`

### Priority Order

1. **Focus active**: If `focusId` is set, camera cache is not restored
2. **Geolocation initial center**: If initial center is from geolocation, cache is cleared and not restored
3. **Cached camera**: If cache exists and no focus/geolocation, restore cached view
4. **Default**: Use initial center from hook (Rotterdam or geolocation)

## Files Involved

### Core Implementation

- `Frontend/src/hooks/useInitialMapCenter.ts` - Initial center determination hook
- `Frontend/src/hooks/useUserPosition.ts` - Extended geolocation hook (with `autoRequest` option)
- `Frontend/src/lib/geo.ts` - Coverage bounds check (`isWithinRotterdamBounds`)
- `Frontend/src/lib/initialView.ts` - Unclustered marker visibility heuristic
- `Frontend/src/components/MapView.tsx` - Map component with initial view integration
- `Frontend/src/components/mapCameraCache.ts` - Camera state persistence

### Configuration

- `Frontend/src/lib/config.ts` - Map defaults, cluster config, zoom levels
- `Infra/config/cities.yml` - City bbox definitions (reference)

## Testing Scenarios

### Scenario A: Geolocation Granted & Within Rotterdam

1. Grant geolocation permission in browser
2. Set test position within Rotterdam bounds
3. Reload app
4. **Expected**: Map centers near user, at least one marker visible and unclustered

### Scenario B: Geolocation Denied / Blocked

1. Block location in browser settings
2. Reload app
3. **Expected**: Map defaults to Rotterdam, at least one marker visible, no permission dialogs

### Scenario C: Geolocation Granted But Outside Coverage

1. Grant permission, simulate location far outside Rotterdam (e.g., another country)
2. Reload app
3. **Expected**: App detects "outside coverage" and falls back to Rotterdam, behavior matches Scenario B

## Edge Cases & Trade-offs

### Edge Cases

- **Permissions API not supported**: Falls back to Rotterdam (no geolocation attempt)
- **Geolocation timeout**: 8s timeout, then fallback to Rotterdam
- **Invalid coordinates**: Non-finite lat/lng values trigger fallback
- **Empty dataset**: Heuristic returns null, keeps initial zoom
- **Map not ready**: Heuristic waits for `mapReady` and source availability
- **Active transitions**: Heuristic waits if `cameraBusyRef.current` is true

### Trade-offs

- **No auto-prompt**: Respects user privacy but may not use geolocation if user hasn't granted permission yet
- **Coverage bounds**: Hard-coded bbox may need updates if coverage expands
- **Cluster expansion**: Uses async `getClusterExpansionZoom`, may cause slight delay
- **Camera cache**: Cleared for geolocation to prioritize user location over cached view

## Future Improvements

- Support for multiple cities (dynamic bbox lookup)
- Polygon-based coverage detection (instead of simple bbox)
- User preference to remember geolocation choice
- Progressive enhancement: show Rotterdam immediately, then adjust if geolocation resolves


# Map Cluster Configuration

## Overview

This document describes the Mapbox clustering configuration for the Turkish Diaspora App map view. Clustering groups nearby markers together at lower zoom levels to improve performance and readability, then expands to show individual markers as users zoom in.

## Configuration Parameters

All cluster parameters are defined in `Frontend/src/lib/config.ts` under the `CLUSTER_CONFIG` export:

### `MAX_ZOOM: 15`
- **Type:** `number`
- **Default:** `15` (increased from 14)
- **Description:** Maximum zoom level at which clustering occurs. Above this zoom level, all markers are displayed individually.
- **Effect:** Higher values mean clustering continues at higher zoom levels, showing more individual markers at district-level zoom (Z ≈ 12-14).

### `RADIUS: 30`
- **Type:** `number`
- **Default:** `30` (reduced from 50)
- **Description:** Radius of each cluster when clustering points. Measured in pixels.
- **Effect:** Smaller values create tighter clusters with fewer markers per cluster, resulting in more individual markers visible at mid-range zoom levels.

### `MOBILE_MAX_ZOOM: 16`
- **Type:** `number`
- **Default:** `16`
- **Description:** Maximum zoom level for clustering on mobile devices. Slightly higher than desktop to account for smaller screens.
- **Effect:** Mobile devices can handle slightly higher zoom before clustering stops, providing better detail on smaller screens.

### `MOBILE_RADIUS_MULTIPLIER: 0.8`
- **Type:** `number`
- **Default:** `0.8`
- **Description:** Multiplier applied to `RADIUS` on mobile devices.
- **Effect:** Mobile uses 80% of desktop radius (24px vs 30px), creating tighter clusters for better clarity on smaller screens.

## Desktop vs Mobile Behavior

The clustering system automatically detects mobile devices using `isMobile()` utility (viewport width < 768px) and applies different configurations:

**Desktop:**
- `clusterMaxZoom: 15`
- `clusterRadius: 30`

**Mobile:**
- `clusterMaxZoom: 16`
- `clusterRadius: 24` (30 × 0.8)

This ensures optimal marker visibility on both device types.

## How Clustering Works

1. **At low zoom levels (Z < 12):** Markers are aggressively clustered into groups
2. **At mid zoom levels (Z 12-15):** Clustering becomes less aggressive, showing more individual markers
3. **At high zoom levels (Z > 15):** All markers are displayed individually (no clustering)

## Source Recreation

Mapbox GeoJSON sources are **immutable** after creation. The cluster configuration (`clusterMaxZoom` and `clusterRadius`) cannot be changed on an existing source.

### Automatic Recreation

The system automatically detects when cluster configuration changes and safely recreates the source:

1. **Detection:** Compares current config with stored config per map instance
2. **Removal:** Removes all dependent layers in reverse dependency order
3. **Recreation:** Removes old source, creates new source with updated config
4. **Restoration:** Re-adds all layers and restores existing GeoJSON data

### When Recreation Occurs

- Initial map load (first time)
- Device orientation change (mobile ↔ desktop breakpoint)
- Configuration changes in code (development/testing)

### Safety Guarantees

- **No data loss:** Existing GeoJSON data is preserved during recreation
- **No map remounts:** Map instance remains stable
- **Idempotent:** Multiple calls to `ensureBaseLayers()` are safe
- **Layer order preserved:** Layers are recreated in correct dependency order

## Tuning Guidelines

### To Show More Individual Markers

**Increase `MAX_ZOOM`:**
```typescript
MAX_ZOOM: 16  // Clustering stops earlier, more individual markers visible
```

**Decrease `RADIUS`:**
```typescript
RADIUS: 25  // Tighter clusters, fewer markers per cluster
```

### To Show More Clusters

**Decrease `MAX_ZOOM`:**
```typescript
MAX_ZOOM: 13  // Clustering continues longer, more clusters visible
```

**Increase `RADIUS`:**
```typescript
RADIUS: 40  // Larger clusters, more markers per cluster
```

### Mobile-Specific Tuning

Adjust `MOBILE_MAX_ZOOM` and `MOBILE_RADIUS_MULTIPLIER` independently:

```typescript
MOBILE_MAX_ZOOM: 17  // Even higher zoom before clustering stops on mobile
MOBILE_RADIUS_MULTIPLIER: 0.7  // Even tighter clusters on mobile (21px)
```

## Performance Considerations

### Marker Count Impact

- **Low marker count (< 100):** Clustering has minimal impact
- **Medium marker count (100-500):** Clustering improves performance significantly
- **High marker count (500+):** Clustering is essential for smooth rendering

### Zoom Level Impact

- **Low zoom (Z < 10):** Clustering dramatically improves performance
- **Mid zoom (Z 10-15):** Balanced clustering and individual markers
- **High zoom (Z > 15):** All individual markers, performance depends on marker count

### Mobile Performance

Mobile devices benefit from:
- Tighter clusters (smaller radius)
- Slightly higher max zoom (better detail)
- Reduced visual clutter

## Technical Implementation

### Files Involved

- `Frontend/src/lib/config.ts` - Configuration constants
- `Frontend/src/lib/utils.ts` - `isMobile()` utility
- `Frontend/src/components/markerLayerUtils.ts` - Source creation and recreation logic
- `Frontend/src/components/MarkerLayer.tsx` - React component managing marker rendering
- `Frontend/src/components/MapView.tsx` - Map container with viewport handling

### Key Functions

**`getClusterConfig()`**
- Calculates current cluster configuration based on device type
- Called during source creation and recreation

**`recreateSourceWithConfig()`**
- Safely removes old source and layers
- Creates new source with updated configuration
- Restores all layers and data

**`ensureBaseLayers()`**
- Main entry point for layer management
- Detects config changes and triggers recreation if needed
- Idempotent and safe to call multiple times

## Viewport Fetch Suppression

When users click to expand a cluster, the map programmatically zooms in. To prevent unnecessary API fetches during this programmatic zoom, the system calls `onSuppressNextViewportFetch()` before the camera transition.

This ensures that:
- Cluster expansion doesn't trigger viewport-based location fetches
- User-initiated zoom still triggers fetches normally
- Performance is optimized by avoiding redundant API calls

## Troubleshooting

### Markers Not Clustering

1. Check that `cluster: true` is set in source configuration
2. Verify `clusterMaxZoom` is appropriate for current zoom level
3. Ensure source was created with clustering enabled

### Too Many/Few Clusters

1. Adjust `RADIUS` (smaller = more clusters, larger = fewer clusters)
2. Adjust `MAX_ZOOM` (higher = clustering stops earlier)
3. Test at different zoom levels to find optimal balance

### Performance Issues

1. Verify clustering is enabled (essential for 500+ markers)
2. Check marker count in viewport
3. Monitor FPS on mobile devices
4. Consider reducing `MAX_ZOOM` if too many individual markers

### Source Recreation Issues

1. Ensure `ensureBaseLayers()` is called after style loads
2. Check that layers are removed before source removal
3. Verify layer recreation order matches dependencies
4. Check browser console for Mapbox errors

## Related Documentation

- [Map UX Upgrade](./map-ux-upgrade.md) - Overall map improvements
- [Frontend Modes](./frontend-modes.md) - Map interaction modes
- [Discovery OSM](./discovery-osm.md) - Location discovery system


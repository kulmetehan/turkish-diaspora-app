---
title: Map UX Upgrade — Mapbox GL
status: active
last_updated: 2025-11-04
scope: frontend
owners: [tda-ux]
---

# Map UX Upgrade — Mapbox GL

Summary of the Mapbox migration (Fase 3) and guidelines for maintaining the map experience.

## Goals

- Replace Leaflet with Mapbox GL for smoother interactions and vector tile styling.
- Maintain familiar Google/Apple-like gestures (pinch, rotate, tilt) while staying performant on mobile devices.
- Integrate with the bottom sheet and search/filter flow.

## Implementation highlights

- Map entry: `Frontend/src/components/map/MapView.tsx` (wraps Mapbox GL and syncs with `mapStore`).
- Marker rendering: derived from verified locations returned by `/api/v1/locations`.
- Clustering: currently disabled; consider enabling once we expand to more cities.
- Styling: controlled via Mapbox style (default `mapbox://styles/mapbox/light-v11`), configurable via `VITE_MAPBOX_STYLE` if needed.
- Performance: reuse a single Mapbox instance, throttle updates via store selectors to avoid excessive re-renders.

## Token & environment

- Mapbox publishable token stored in `VITE_MAPBOX_TOKEN`.
- Restrict token usage to localhost + GitHub Pages domain via Mapbox dashboard.
- Optional: provide fallback styling for offline development (replace Mapbox with dummy grid).

## UX guidelines

- Keep marker interactions simple: tap to highlight, show details in sheet.
- Ensure bottom sheet and map transitions stay synchronized (center map on selected item).
- Provide helpful empty states when filters yield no results.
- Maintain high-contrast markers for verified locations; consider category-specific icons in future iterations.

## Testing

- Verify touch gestures on iOS Safari and Android Chrome.
- Ensure markers update when category/search filters change.
- Confirm map resizes correctly when bottom sheet transitions between snap points.
- Validate Mapbox token error handling (surface a friendly message instead of breaking the UI).

## Next steps

- Investigate marker clustering when dataset grows.
- Explore heatmap layers for discovery monitoring.
- Integrate Mapbox offline tiles or caching if needed for field operations.

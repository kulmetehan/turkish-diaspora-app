## Map Marker Stability QA

- **Initial load**: Hard refresh the deployed build, confirm clusters and single markers render without style warnings.
- **Pan / zoom**: Drag and zoom repeatedly; map stays mounted, markers persist, no blank frames and console stays clean.
- **Selection cycle**: Click a list item to focus the marker, verify popup opens, close it via map tap or `X` and ensure no reload.
- **Viewport fetch**: Watch Network tab; `moveend` triggers a single debounced `/locations?bbox=…` request and cancels in-flight ones.
- **Zoomed-out fallback**: Zoom out fully; app falls back to `/locations/count` + paginated `/locations` requests and markers continue to render.


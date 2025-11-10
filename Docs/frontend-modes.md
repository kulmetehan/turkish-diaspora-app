# Frontend View Modes

The public map screen now supports two mutually exclusive presentation modes that share the same data state.

- **Hash routing** – The current mode is stored in the hash query as `view=list` or `view=map`, for example `#/?view=list`. Missing or unknown values default to `map`.
- **Shared data layer** – `App` owns the fetch pipeline (`all` + `filtered` arrays) and reuses it for both modes, so switching views does not re-fetch locations or reset filters.
- **Toggle control** – The view selector lives inside the Filters component (tabs styled with shadcn/ui). Toggling updates the hash without a full reload and keeps filters/search/selection intact.
- **Deep links & history** – Loading a hash link opens the corresponding mode immediately. Browser back/forward changes the view by emitting `hashchange`, handled by `onViewModeChange`.
- **Map focus** – When the list triggers “Toon op kaart”, the hash briefly adds `focus=<id>`. `App` passes this to `MapView`, which animates to the location, keeps the marker + tooltip visible, and only clears the `focus` parameter after the motion completes.
- **Camera persistence** – `MapView` stores center/zoom/bearing/pitch when unmounted and restores them on the next mount (unless a new `focus` is active), so returning to the map feels continuous instead of resetting to defaults.
- **Mobile & desktop** – Desktop renders either the map overlay or the list column. Mobile keeps the list inside the bottom sheet, while the map mode shows the filters as a floating card.

Developers adding new features should reuse the existing helpers in `Frontend/src/lib/routing/viewMode.ts` (`readViewMode`, `writeViewMode`, `readFocusId`, `writeFocusId`, `clearFocusId`) to stay aligned with this contract.

## Map Tooltip Lifecycle (TDA-107)

- `MapView` owns a single Mapbox popup instance via the popup controller; it survives re-renders and only detaches on unmount or explicit hide, keeping the tooltip stable across List → Map transitions.
- Marker colouring now relies on Mapbox `feature-state.selected`; `MarkerLayer` toggles the state so the focused marker goes green while clearing the previous selection.
- The popup controller listens to `move`, `moveend`, `idle`, and `styledata` to recompute anchor classes, keeping the arrow visible even when the camera stops animating.
- Camera cache behaviour is unchanged: the controller never recreates the map, so `restoreCamera`/`storeCamera` continue to work without triggering cold reloads or extra fetches.


## Map Controls (F4-S5)

- `MapControls.tsx` renders the North reset and My Location actions as a floating stack in the map container; the overlay respects safe-area insets so it stays clear of the mobile bottom sheet.
- `MapView` wires both actions through `performCameraTransition`. Before calling `easeTo`, the handlers invoke `onSuppressNextViewportFetch`, which toggles the one-shot guard in `App` so programmatic moves avoid triggering viewport-driven refetches.
- The North button keeps the current center/zoom/pitch and only normalises the bearing to `0`, giving a smooth compass reset.
- The My Location button uses `navigator.geolocation.getCurrentPosition` with high-accuracy hints. It eases to the device location, clamps the zoom to `CONFIG.MAP_MY_LOCATION_ZOOM` (default `14`), and logs concise console notices when permissions are denied or the position is unavailable.


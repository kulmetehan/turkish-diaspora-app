# Frontend Overlay Detail Card

## Overview

The overlay detail card (feature flag **F4-S2**) surfaces rich information and quick actions for a selected location. It replaces lightweight inline details with a dedicated modal (desktop) or full-screen sheet (mobile).

## Interaction Flow

- A selection from the map markers or location list opens the overlay.
- While open, the Mapbox canvas is set to `pointer-events: none` so users cannot pan, zoom, or interact with markers.
- Closing the overlay (X button, ESC key, or backdrop click) clears the selection and restores map interactivity.

## Actions

- **Route** — Detects platform to launch directions.
  - iOS: `maps://?q=<name>&ll=<lat>,<lng>` (Apple Maps deep link).
  - Android / Desktop: `https://www.google.com/maps/dir/?api=1` with `destination` and optional `destination_place_id`.
  - Falls back to `q=<name>` when coordinates are missing.
- **Google Search** — Opens `https://www.google.com/search?q=<name> <city>` in a new tab. City is parsed from the address when possible and defaults to “Rotterdam”.

Both actions use `rel="noopener noreferrer"` and `target="_blank"` where appropriate.

## Accessibility

- Implemented with Radix Dialog primitives (via shadcn/ui) to inherit focus trapping, ESC-to-close, and backdrop semantics.
- Buttons expose descriptive `aria-label`s (e.g., “Open route in Maps”, “Search on Google”, “Close details”).
- Body scrolling is locked while the dialog is open; no scroll bleed on mobile.
- The dialog title is associated via `aria-labelledby`, and supporting content is referenced with `aria-describedby`.

## Layout Notes

- Mobile (`<1024px`): full-height overlay with sticky action bar at the top; content scrolls independently.
- Desktop (`≥1024px`): centered dialog capped at ~840px width with rounded corners and shadow.
- Category badge, Turkish verification chip, and confidence metrics mirror existing list styling for visual continuity.

## Testing Checklist

- Map stays static while overlay is open; pointer events restored immediately after closing.
- Route button deep-links correctly on iOS Safari, Android Chrome, and desktop browsers.
- Google search button opens a new tab with “<name> <city>”.
- Keyboard navigation cycles within the dialog and ESC closes it.
- Overlay reacts correctly when switching between locations without closing first.*** End Patch


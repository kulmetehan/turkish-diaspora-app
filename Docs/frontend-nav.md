# Frontend Navigation — Mobile Tabs

## Overview

- Mobile navigation now uses a fixed footer bar at `Frontend/src/components/FooterTabs.tsx`.
- Tabs: `Feed`, `News`, `Map`, `Events`, `Account`. The map remains the default landing experience.
- Routes live under the HashRouter (`#/map`, `#/feed`, `#/news`, `#/events`, `#/account`) and work with `import.meta.env.BASE_URL` for GitHub Pages deployments.

## Implementation Notes

- The footer bar is `fixed` with safe-area padding (`pb-[env(safe-area-inset-bottom)]`) to avoid the iOS home indicator.
- Navigation uses `NavLink`, so `aria-current="page"` and active styling stay in sync without reloads.
- `AppLayout` in `Frontend/src/main.tsx` adds `pb-[calc(84px+env(safe-area-inset-bottom))]` on mobile to keep content clear of the footer.

## Deployment & BASE_URL

- `HashRouter` runs without a `basename`; routing stays hash-based (`#/map`, etc.) regardless of the GitHub Pages sub-path.
- Vite still needs `base=/turkish-diaspora-app/` for asset URLs. On local previews, run `npm run build` (which uses that base), then `npm run preview` and set `window.location.pathname = "/turkish-diaspora-app/"` before refreshing to mimic Pages.
- Deep links (e.g., `#/events`) continue to resolve under the Pages deployment.

## Safe-Area & A2HS Tips

- When testing Add-to-Home-Screen on iOS, ensure the safe-area padding remains; the footer respects dynamic `env(safe-area-inset-bottom)` values.
- Avoid placing additional fixed elements at the bottom unless they also apply safe-area padding to prevent overlap.

## QA Checklist

- [ ] Footer remains fixed while scrolling on iOS/Android.
- [ ] Active tab highlight updates via SPA navigation (no full reloads).
- [ ] `#/` redirects to `#/map`.
- [ ] Deep links (`#/events`, `#/account`) load under the configured `BASE_URL`.
- [ ] Map interaction does **not** auto re-center when selecting markers or list items (unless `centerOnSelect` is explicitly enabled).


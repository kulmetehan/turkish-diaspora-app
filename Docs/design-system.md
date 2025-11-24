---
title: Design System Guide
status: active
last_updated: 2025-11-24
scope: frontend
owners: [tda-ux]
---

# Design System Guide

Guidelines for the Turkish Diaspora App UI across the public map and admin dashboard.

## Stack recap

- **Framework**: React 19 + TypeScript with Vite.
- **Styling**: Tailwind CSS with CSS variables for tokens.
- **Components**: shadcn/ui pattern (`class-variance-authority`, `tailwind-merge`) implemented in `Frontend/src/components/ui/`.
- **Icons**: `lucide-react` rendered via `<Icon name="..." />` wrapper.
- **Toasts**: `sonner`.

## Tokens

Defined primarily in `Frontend/src/index.css` and `Frontend/src/lib/theme/darkMode.ts`.

| Category | Variables |
| --- | --- |
| Color | `--background`, `--foreground`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--border`, `--input`, `--ring`. |
| Radius | `--radius-sm`, `--radius-md`, `--radius-lg`. |
| Shadow | `--shadow-soft`, `--shadow-card`. |
| Spacing | `--space-grid-gutter`, contextual Tailwind spacing utilities. |
| Gradient | `--gradient-main`, `--gradient-nav`, `--gradient-card` (also exposed via Tailwind `bg-gradient-*`). |

### Surfaces

- `.bg-brand-surface` → Main app shell gradient + body background.
- `.bg-brand-surface-alt` → Overlay and panel backdrop with blur baked in.
- Use `bg-surface-raised`, `bg-surface-muted`, and `bg-surface-contrast` Tailwind colors inside cards for layered depth.
- Map/list containers always sit on one of these surfaces to avoid flashing white when switching modes.

### Brand Colors

Turkspot brand colors are integrated into the design system via CSS variables and Tailwind tokens.

| Variable | Tailwind Token | Usage |
| --- | --- | --- |
| `--brand-red-strong` | `from-brand-redStrong`, `text-brand-redStrong` | Ferrari highlight for halos, gradients, and CTA glows. |
| `--brand-red` | `bg-brand-red`, `text-brand-red` | Primary action color (maps to `--primary`). |
| `--brand-red-soft` | `bg-brand-redSoft` | Soft overlays, selected states, subtle chips. |
| `--brand-accent` | `bg-brand-accent` | Semantic alias for current accent hue (light/dark aware). |
| `--brand-white` | `text-brand-white`, `bg-brand-white` | Foreground on red backgrounds and inverse surfaces. |

**Light mode values (HSL):**
- `--brand-red-strong`: `357 94% 45%`
- `--brand-red`: `0 86% 55%`
- `--brand-red-soft`: `4 82% 68%`
- `--brand-white`: `0 0% 100%`

**Dark mode values (HSL):**
- `--brand-red-strong`: `357 88% 64%`
- `--brand-red`: `0 78% 62%`
- `--brand-red-soft`: `4 78% 70%`
- `--brand-white`: `0 0% 100%`

**Usage guidelines:**
- **Primary actions** → `bg-primary` / `bg-brand-red` with `text-brand-white`
- **Header & hero surfaces** → `bg-gradient-main` or `bg-gradient-nav` utilities
- **Card halos / chips** → `bg-brand-redSoft` or `bg-gradient-card` for elevated states
- **Error/destructive** → Use `bg-destructive`; do not repurpose Ferrari red

The `--primary` / `--primary-foreground` variables are mapped to the current accent hues, so shadcn/ui primitives stay on-brand without hardcoded reds. Tailwind exposes gradients via `bg-gradient-main`, `bg-gradient-nav`, and `bg-gradient-card`.

### Dark mode

- Controlled via `class` strategy (toggle `.dark` on `<html>`).
- Implementation: `Frontend/src/lib/theme/darkMode.ts` (`initTheme`, `setTheme`, `getTheme`).
- Honor system preference (`prefers-color-scheme`) when `mode = "system"`.

## Component conventions

- House reusable primitives in `Frontend/src/components/ui/`. Export component + types from each file.
- Use `cva` for variants and size modifiers.
- Keep markup semantic (buttons vs. anchors, labels for inputs, etc.).
- Accessibility defaults: visible focus ring, ARIA labels for icons (or `aria-hidden` when decorative), trap focus in dialogs (Radix primitives assist).

## Layout patterns

- **Map + list**: `Frontend/src/components/map/` + `Frontend/src/pages/AdminHomePage.tsx` coordinate layout.
- **Bottom sheet**: `Frontend/src/components/bottom-sheet/` plus QA checklist in `Docs/qa/bottom-sheet-test.md`.
- **UI Kit**: `Frontend/src/pages/UiKit.tsx` showcases available components.

## Guidelines

1. Favor composable primitives (Button, Card, Input, Select, Tabs, Dialog, Sheet, Toast).
2. Avoid inline colors; use token-based Tailwind classes (`bg-primary`, `text-foreground`).
3. Keep primary actions obvious (single main CTA per view, 150–200ms micro-animations maximum).
4. Maintain consistent spacing/typography with Tailwind utility scales.
5. Document new component usage in the UI kit and update this guide if tokens change.

## Accessibility checklist

- Keyboard navigation fully supported (tab order, skip links where necessary).
- Minimum contrast: WCAG AA (>=4.5:1 for text, 3:1 for large text/icons).
- Modals/dialogs trap focus; close on ESC.
- Provide alternative text for imagery; use icon wrappers with `title` when icons convey meaning.

## References

- Component library directory: `Frontend/src/components/ui/`
- Theme helpers: `Frontend/src/lib/theme/darkMode.ts`
- Map layout: `Frontend/src/components/map/`
- QA checklist: `Docs/qa/bottom-sheet-test.md`

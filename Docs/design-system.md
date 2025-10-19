# Design System – Turkish Diaspora App (Fase 3)

Doel: uniforme, minimalistische UI met **Apple-simplicity** en **Google-familiarity**. Deze gids definieert tokens, componentregels, dark mode en werkwijze voor nieuwe componenten.

## Stack
- React + Vite + TypeScript
- TailwindCSS (class strategy), tokens via CSS vars
- shadcn/ui-stijl (CVA + tailwind-merge) – handmatig beheerde componenten in `src/components/ui`
- lucide-react icons via `<Icon name="…"/>`
- Radix primitives (Dialog, Tabs, Select)
- sonner (toasts)

## Tokens
Bron: `src/index.css` en `src/lib/ui/theme.ts`.  
Belangrijkste variabelen:
- Kleuren: `--background`, `--foreground`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, plus `--border`, `--input`, `--ring`.
- Radius: `--radius-lg|md|sm`
- Schaduw: `--shadow-soft`, `--shadow-card`
- Spacing: `--space-grid-gutter`

### Dark Mode
- Strategie: `class` – root `html` krijgt/ontneemt `.dark`.
- Implementatie: `src/lib/theme/darkMode.ts` (`initTheme`, `setTheme`, `getTheme`).
- Sync met systeem via `prefers-color-scheme` wanneer instelling `system` is.

## Componentregels
- **No ad-hoc UI**: Gebruik eerst `src/components/ui/*`. Mist iets? Voeg toe volgens CVA-patroon.
- **Focus state**: rely op Tailwind ring tokens (`ring-ring`, `ring-offset-background`).
- **Accessibility**:
  - Toetsenbordfocus overal zichtbaar.
  - Iconen zijn *decorative* (`aria-hidden`) tenzij semantisch nodig → dan `decorative={false}` + `title`.
  - Contrast ≥ WCAG AA; voorkom lichtgrijze tekst op lichte achtergrond.
  - Dialogs: Radix focus trapping.
- **Performance**: Geen globale zware CSS; component-scoped utility klassen. Tree-shake imports.

## Nieuwe component toevoegen (How-to)
1. Maak bestand in `src/components/ui/<naam>.tsx`.
2. Gebruik `cva` voor varianten/sizes; exports: `Component` + types.
3. Voeg minimale styles toe (base + variant).
4. Story in UI Kit? Voeg section toe in `src/pages/UiKit.tsx`.

## Iconen
- Gebruik `<Icon name="MapPin" />`. Beschikbare namen = exports van `lucide-react`.
- Titles alleen voor non-decorative gebruik; anders `aria-hidden`.

## Richtlijnen (Apple simplicity × Google familiarity)
- Mobiel eerst; rust en whitespace.
- Primair action-pad duidelijk en simpel (max 1–2 primary buttons per view).
- Micro-animaties ≤ 150–200ms, subtiel (fade/scale).
- Vermijd jargon; korte labels.
- List/Map blijft functioneel en snel (Leaflet-view: geen regressies).

## Koppeling met komende stories
- **Bottom Sheet**: hergebruik tokens (radius, shadows), Radix Sheet of custom `Dialog` variant.
- **Search redesign**: Input + Tabs + Badge als filters; consistent met tokens.
- **Admin UI**: kaarten en formulieren met `Card`, `Input`, `Select`, `Tabs`, `Dialog`, `Toast`.

## Changelog (v1)
- Tailwind + tokens
- UI-bibliotheek (Button, Card, Input, Label, Select, Tabs, Dialog, Badge, Toast)
- Icon wrapper
- Dark mode (system + toggle)
- UI Kit pagina
- Kleine refactor: Header/Nav + primary button

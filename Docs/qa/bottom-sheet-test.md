---
title: Bottom Sheet QA Checklist
status: active
last_updated: 2025-11-04
scope: frontend
owners: [tda-qa]
---

# Bottom Sheet QA Checklist

Manual regression guide for the Google-Maps-style bottom sheet used on mobile and narrow viewports.

## Acceptance criteria

- Drag gesture is smooth (no stutter); settle into snap point within ~250–350 ms.
- Snap points correct: collapsed `64px`, half `45vh`, full `94vh`; apply resistance near limits.
- At full height, list scroll gestures do not pull the sheet; downward drag transfers control back to sheet when list is at top.
- Velocity-based flings choose the nearest snap point (up vs. down) based on momentum.
- Backdrop only visible at full height; tapping backdrop returns to half height.
- Keyboard interactions: `Esc` collapses one step, `Enter`/`Space` on handle toggles half/full.
- No passive listener warnings in console; transform/opacity only (no layout thrash).
- Works on iOS Safari and Android Chrome.

## Edge cases

- Rapid tap–drag–release does not produce jittery bounce.
- Orientation changes recompute snap points and maintain logical state.
- Virtual keyboard does not force sheet to full height unless necessary.

## Test script

1. **Basic drag & snap**
   - Drag from collapsed to half, release near snap point → sheet settles at half.
   - Drag from half to full, release → full height with backdrop.
   - Drag beyond limits → resistance, no overscroll glow.

2. **Velocity-based fling**
   - From collapsed, fast upward swipe → full if velocity high, otherwise half.
   - From full, fast downward swipe → half or collapsed depending on speed.

3. **Scroll handoff**
   - At full, scroll inside list → sheet remains fixed.
   - When list is at top, drag downward → sheet takes over immediately.

4. **Backdrop & keyboard**
   - With sheet full, tap backdrop → half state.
   - Focus handle, press `Esc` → full → half → collapsed.
   - Press `Enter`/`Space` on handle → toggle between states per spec.

5. **Orientation & IME**
   - Rotate device → snap points recompute, state coherent.
   - Focus an input inside sheet → keyboard does not create layout jump; drag remains smooth.

6. **Performance**
   - Record long drag (DevTools Performance) → only transform/opacity change, 60 fps on mid-tier devices.
   - Verify no layout recalculations during animation frames.

7. **Cross-browser**
   - iOS Safari: no rubber-band issues, handoff works.
   - Android Chrome: gestures smooth, no console warnings.

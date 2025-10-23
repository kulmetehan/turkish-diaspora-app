Google-Maps-style Bottom Sheet – Manual QA Checklist

Acceptance Criteria
- Drag is smooth (no stutter); settle to snap in ~250–350ms
- Snap points correct: 64px / 45vh / 94vh; resistance near limits
- At full, vertical swipe inside list scrolls list; downward at top transfers to sheet
- Fling up from collapsed goes to half/full based on velocity/distance
- Backdrop only in full; tap backdrop snaps to half
- Escape collapses one step; Enter/Space on handle toggles half/full
- Performance profile: only transform/opacity updates; no layout shifts
- No passive listener violations in console
- Works on iOS Safari and Android Chrome

Edge Cases
- Rapid tap-drag-release does not bounce incorrectly
- Orientation change recomputes snap points and re-snaps logically
- Virtual keyboard: sheet does not fight input; no forced full unless necessary

Test Steps
1) Basic Drag and Snap
   - Drag from collapsed → release near half: snaps to half
   - Drag from half → release near full: snaps to full
   - Drag past limits: resistance felt; no overscroll glow

2) Velocity-based Fling
   - From collapsed, fast upward swipe: full (if velocity high), else half
   - From full, fast downward swipe: half/collapsed depending on momentum

3) Scroll Handoff
   - At full, scroll list; sheet remains fixed
   - While list at top, drag downward: control transfers to sheet immediately

4) Backdrop and Keyboard
   - In full state, tap backdrop: snaps to half
   - Focus handle; press Esc: full → half → collapsed
   - Enter/Space on handle: collapsed ↔ half ↔ full per spec

5) Orientation & IME
   - Rotate device: snap points update; state stays coherent
   - Focus input inside content: keyboard does not cause jank; dragging remains smooth

6) Performance Profiling
   - Record long drag; verify only transform/opacity change; 60fps on mid devices
   - No layout recalculations during rAF frames beyond minimal reads

7) Cross-browser
   - iOS Safari: no rubber-banding; handoff works
   - Android Chrome: smooth drags; passive listener warnings absent



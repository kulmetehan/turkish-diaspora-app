
⸻

📄 EPIC-7-MAP-UX-POLISH.md

Turkish Diaspora App — EPIC 7
Titel: Map UX Polish & Pre-Alpha Readiness
Versie: 1.0
Datum: 2025

⸻

🎯 Epic Summary

This epic focuses on transforming the Map, List, News, and Events UX into a cohesive, smooth, stable, high-quality interface that feels like a true native application.
The goal is to remove the remaining friction points, increase visual and interaction consistency, and ensure the app is fully ready for soft-launch (Alpha Release).

The work in this epic drastically improves:
	•	Interaction stability
	•	Visual cohesion
	•	Navigation ergonomics
	•	Performance & clarity
	•	Professional polish

This is the final UX milestone before public testing.

⸻

🧩 Motivation

Through user testing and internal review, several UX gaps were identified:
	•	Sudden camera movements during marker selection harm usability
	•	Default Mapbox cluster styling no longer matches the Turkspot identity
	•	Tabs reset their entire state when switching (breaking user flow)
	•	Page shells are inconsistent, causing the UI to feel “modular” instead of unified
	•	List view wastes space and uses oversized card shells
	•	Highways (A/N roads) are visually noisy
	•	A macro-level navigation layer would significantly improve overview when zoomed out

Solving these issues is essential for Alpha.

⸻

🛠️ Scope

This epic includes improvements across:

✔ Map interaction model

✔ Map clustering and zoom hierarchy

✔ State persistence and navigation memory

✔ Visual redesign of list/news/event shells

✔ Map style cleanup

✔ Heatmap-based country-level navigation (optional for Alpha)

✔ Final QA and polish

Out-of-scope:
	•	Backend changes to discovery, classification, metrics
	•	New database tables
	•	New admin features
	•	Major redesign of general branding (part of EPIC 5)

⸻

📌 User Stories

⸻

US-P1 — Disable Auto-Center & Auto-Zoom on Marker Selection

Goal: Selecting a marker should not move the camera.
Problem: Current behavior jumps/zooms → disorienting.
Solution: Remove camera updates on marker click. Tooltip only.

Acceptance Criteria
	•	No zoom, pan, center change on selection
	•	Tooltip opens directly above marker
	•	Selecting a different marker closes the previous tooltip
	•	No regressions to clustering or list interactions

⸻

US-P2 — Redesign Map Clusters in Turkspot Style

Goal: Replace generic blue cluster circles with Turkspot UI identity.
Solution: Rounded-square cluster boxes, brand colors, correct padding, clear count.

Acceptance Criteria
	•	No default Mapbox styling remains
	•	Count remains readable at all zoom levels
	•	Style matches design tokens used in category icons
	•	Performance remains stable

⸻

US-P3 — Preserve Navigation State Per Tab

Goal: Navigating away from the map should not reset it.
Solution: Centralized state persistence for Map, News, Events.

Data to persist:
	•	Map zoom
	•	Map center
	•	Active marker
	•	List scroll
	•	Applied filters

Acceptance Criteria
	•	Switching tabs restores exact previous state
	•	No visual jumps
	•	Works for Map ↔ News ↔ Events

⸻

US-P4 — Macro Heatmap Layer (Zoomed-Out Navigation)

Goal: Add a Snapchat-style glowing heatmap layer for national overview.
Solution: When zoomed out, clusters hide → heatmap layer appears.

Features:
	•	Hover intensifies glow
	•	Click zooms into that city’s bounding box
	•	Smooth transitions

Acceptance Criteria
	•	Heatmap appears only past zoom threshold
	•	Hover → glow intensity increase
	•	Click → smooth zoom to clusters
	•	No performance lag

⸻

US-P5 — Hide Highway Labels (A20, A4, N57, etc.)

Goal: Reduce visual clutter from road labels.
Solution: Mapbox style overrides to hide A/N-road text layers.

Acceptance Criteria
	•	Highway and N-road labels hidden
	•	No important POI labels removed
	•	Clean and minimal map look

⸻

US-P6 — Optimize List View (Compact Layout + Remove Filter)

Goal: Increase usability and density of list view.
Problems:
	•	Oversized card shells
	•	“Only Turkish” filter redundant
	•	Too much vertical whitespace

Acceptance Criteria
	•	Filter removed
	•	Cards reduced in height
	•	More items visible per viewport
	•	Consistent spacing and alignment

⸻

US-P7 — Unify Page Shells Across Map, News & Events

Goal: Remove the “loose module” feeling across pages.
Solution: One unified base layout: consistent padding, backgrounds, spacing, radius and shadow rules.

Acceptance Criteria
	•	List view, News, Events share identical foundational layout
	•	No isolated white card islands
	•	Smooth transitions
	•	Visual cohesion equal to top-tier apps

⸻

US-P8 — Pre-Alpha Polishing & Verification

Goal: Final pass before enabling alpha rollout.
Includes:
	•	QA testing across devices
	•	Interaction reviews
	•	Regression checks
	•	Cleanup of legacy code
	•	Performance check for map layers

Acceptance Criteria
	•	No blockers found
	•	UI consistent across all pages
	•	Full documentation updated
	•	Alpha-ready confirmation

⸻

🧨 Risks

Risk	Impact	Mitigation
Removing camera movement may break existing logic	Medium	Audit selection pipeline before Apply
Custom clusters may reduce performance	Medium	Use Mapbox clusterProperties + layer filters
Heatmap layer can be heavy	High	Apply throttling + render only beyond zoom threshold
Unified shells may create regressions	High	Migration per component with visual QA
Tab state persistence may conflict with router	Medium	Persist state using Zustand store or context snapshot


⸻

📅 Dependencies
	•	Requires Mapbox access tokens & style extensibility
	•	Requires Tailwind design tokens (EPIC 5)
	•	Requires existing Map component architecture

No backend dependencies.

⸻

🧭 Workflow (SOP-Compliant)

1. ASK MODE

Analyse codebase for each US (P1 → P8)

2. PLAN MODE

Define exact Work Units:
	•	Each one atomic
	•	Each one minimal scope
	•	No cross-cutting changes in single commit

3. APPLY MODE

Cursor modifies code per Work Unit:
	•	Only required files
	•	Stop on ambiguity
	•	Log impacted files

4. REVIEW

ChatGPT verifies correctness
	•	Regression checks
	•	UX checks
	•	Alignment with design tokens

5. DOCUMENTATION

Update /Docs/EPIC-7/ folder with:
	•	Each user story
	•	Summary of changes
	•	Screenshots (if applicable)
	•	Notes for future improvements

⸻

📌 Success Criteria for the Entire Epic

The epic is considered DONE when:
	•	The map no longer jumps or zooms unexpectedly
	•	Clusters match Turkspot brand identity
	•	Tabs preserve state seamlessly
	•	UI feels unified across all pages
	•	List view uses space efficiently
	•	Road labels no longer distract
	•	Heatmap layer works (optional for Alpha)
	•	Full QA passes
	•	App feels “production-ready” for Alpha launch

⸻

---
title: Documentation Gap Analysis
status: active
last_updated: 2025-11-04
scope: meta
owners: [tda-core]
---

# Documentation Gap Analysis

All markdown documents were refreshed in this audit. The list below tracks remaining follow-ups and future improvements.

| Topic | Follow-up |
| --- | --- |
| Self-verifying worker | Decide whether to implement a combined `self_verify` workflow or continue sequencing `classify_bot` + `verify_locations`. Update `Docs/self-verify-loop.md` when a decision is made. |
| Discovery reports | `Docs/osm-discovery-report-rotterdam.md` now points to the canonical backend report. Consider merging reports or automating report generation for future city rollouts. |
| Metrics expansion | When new cities are added, update `Infra/monitoring/metrics_dashboard.md` and metrics snapshot to cover additional bounding boxes. |
| Frontend roadmap | Document any new UI enhancements (e.g., clustering, analytics) in `Docs/design-system.md` and `Docs/map-ux-upgrade.md` as they ship. |

Add new rows as we discover further gaps.

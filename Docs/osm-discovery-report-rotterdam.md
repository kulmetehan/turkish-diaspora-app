---
title: OSM Discovery Report — Rotterdam (Summary)
status: archive
last_updated: 2025-11-04
scope: data-ops
owners: [tda-core]
---

# OSM Discovery Report — Rotterdam (Summary)

The authoritative production postmortem for the Rotterdam rollout lives in [`Backend/OSM_Discovery_Report_Rotterdam_Production.md`](../Backend/OSM_Discovery_Report_Rotterdam_Production.md). That document includes configuration, execution metrics, endpoint rotation stats, and recommendations.

This file remains as a lightweight pointer for historical context. Key highlights:

- 151+ Turkish-oriented locations discovered across three parallel chunks.
- Strict OSM rate limiting (`0.07 QPS`, backoff `20,60,180,420`) respected.
- Endpoint rotation across `overpass-api.de`, `z.overpass-api.de`, `overpass.kumi.systems`, `overpass.openstreetmap.ru`.
- Zero malformed payloads; JSON parsing fortified against mirror quirks.
- Next rollout targets: The Hague → Amsterdam → Utrecht.

For detailed configuration, logs, and SQL snippets, reference the backend report above.

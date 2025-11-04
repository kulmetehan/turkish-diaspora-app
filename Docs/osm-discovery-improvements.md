---
title: OSM Discovery Pipeline Improvements
status: active
last_updated: 2025-11-04
scope: data-ops
owners: [tda-core]
---

# OSM Discovery Pipeline Improvements

Summary of hardening steps applied to the OSM discovery pipeline during TDA-107.

## Objectives

- Stay fully compliant with OSM/Overpass usage policies.
- Increase coverage in dense city centers without triggering rate limits.
- Produce high-fidelity candidate data with clear audit trails.

## Key improvements

1. **Token bucket rate limiting** — Configurable QPS (`DISCOVERY_RATE_LIMIT_QPS`), sleep base, jitter, and exponential backoff series with mirror rotation.
2. **Adaptive grid subdivision** — Quadtree subdivision up to `MAX_SUBDIVIDE_DEPTH` for high-density cells, reducing duplicate fetches.
3. **Turkish hints mode** — Optional keyword filters (`OSM_TURKISH_HINTS=true`) to boost recall of culturally significant venues.
4. **Duplicate protection** — Combination of `place_id` uniqueness and fuzzy `(name, lat, lng)` checks before insert.
5. **Telemetry logging** — `overpass_calls` table capturing endpoint, status, duration, normalized count, and raw preview for debugging.
6. **Resilient JSON parsing** — Graceful handling when mirrors return strings/HTML instead of JSON; default to empty `elements` to avoid crashes.
7. **Environment templating** — All relevant env vars documented in `/.env.template` and `Docs/env-config.md` for consistency across local and hosted runs.

## Operational checklist

- Rotate contact email in `OVERPASS_USER_AGENT` when ownership changes.
- Monitor `overpass_calls` for elevated 5xx/timeout counts and adjust backoff or sleep base.
- Run dry-run discovery for each category after modifying `categories.yml`.
- Keep GitHub Actions matrices updated when expanding to new cities or adjusting chunk counts.

## Next enhancements

- Parameterize city targets in discovery workflows (beyond Rotterdam).
- Build automated health checks for mirrors (pre-run ping) to skip known outages.
- Enrich telemetry with request/response sizes to quantify Overpass load.

For implementation details consult `services/osm_service.py` and the discovery bot worker source.

# News Feeds – Relevance Thresholds (N2.3)

The news pipeline now exposes six feed types that are assigned purely by AI scores
plus deterministic geo signals. Each feed has a configurable minimum relevance
score stored in `ai_config` so editors can tighten or relax policies without
deploying code.

## Feed Types & Signals

| Feed | Signals (all must be met unless noted) |
|------|----------------------------------------|
| `diaspora` | `relevance_diaspora ≥ threshold`, language NL/TR, and either `location_tag ∈ {local, origin}` or the source category is NL-local/NL-national. |
| `nl` | `relevance_nl ≥ threshold`, language NL, category NL-local/NL-national. |
| `tr` | `relevance_tr ≥ threshold` and language TR or category `tr_national`. |
| `local` | `location_tag = local`, `relevance_nl ≥ threshold`, category NL-local/NL-national. |
| `origin` | `location_tag = origin` and (`relevance_tr ≥ threshold` or category `tr_national`). |
| `geo` | `relevance_geo ≥ threshold` and either category `geopolitiek`/`international` or language EN/FR/DE. |

## Default Thresholds

| Field | Default |
|-------|---------|
| `news_diaspora_min_score` | 0.75 |
| `news_nl_min_score` | 0.75 |
| `news_tr_min_score` | 0.75 |
| `news_local_min_score` | 0.70 |
| `news_origin_min_score` | 0.70 |
| `news_geo_min_score` | 0.80 |

Local/origin feeds allow slightly lower scores because they piggyback on the
deterministic `location_tag` + alias matching layer; the others remain more
conservative to keep noise down.

## Updating Thresholds

Use the admin API to inspect or adjust values:

```
GET /admin/ai/config              # fetch current thresholds
PUT /admin/ai/config              # send partial updates
{
  "news_diaspora_min_score": 0.78,
  "news_geo_min_score": 0.82
}
```

Only send the fields you want to change. All thresholds are validated to stay
between `0.0` and `1.0`, and changes are logged via `ai_config_service`.


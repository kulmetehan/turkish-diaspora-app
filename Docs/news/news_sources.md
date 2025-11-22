# News Sources Config (`configs/news_sources.yml`)

The Diaspora News Intelligence stack loads all RSS feeds from a single YAML
file so new sources can be added without redeploying code.

## Structure

```yaml
version: 1
defaults:
  language: "nl"
sources:
  - name: "Rijnmond – Algemeen"
    url: "https://www.rijnmond.nl/rss"
    language: "nl"
    category: "nl_local"
```

Each entry must include:

- `name`: Human-readable label used for logs/metrics.
- `url`: Full RSS/Atom feed URL (must start with `http://` or `https://`).
- `language`: ISO-style language code (e.g. `nl`, `tr`, `en`).
- `category`: One of:
  - `nl_local`
  - `nl_national`
  - `tr_national`
  - `international`
  - `geopolitiek`

Optional fields (e.g. `region`, `refresh_minutes`) are allowed and stay in the
`raw` metadata for downstream consumers.

## Loader & Validation

- Implemented in `app/models/news_sources.py`.
- Uses `yaml.safe_load`, repo-root path resolution, and structlog logging
  identical to the discovery config loaders.
- Caches parsed results per path; call `clear_news_sources_cache()` in tests or
  after editing the file in long-running processes.
- Invalid rows (missing fields, unsupported category, malformed URL) are logged
  as warnings and skipped so workers keep running.
- Fatal issues (missing file, unreadable YAML, non-list `sources`) are logged as
  errors and return an empty list.

## Worker / CLI Check

- `Backend/scripts/news_sources_check.py` demonstrates how workers import the
  loader. Run:

```bash
cd Backend
python scripts/news_sources_check.py
```

It logs totals per category and surfaces malformed entries via the loader
warnings.

## Adding or Updating Sources

1. Edit `configs/news_sources.yml`.
2. Keep the list alphabetized per category when possible for readability.
3. Ensure every entry includes the required keys and uses HTTPS feeds whenever
   the publisher supports it.
4. Run `python scripts/news_sources_check.py` to confirm the loader accepts the
   file.
5. Run the backend test suite (or at least `pytest Backend/tests/test_news_sources.py`)
   before raising a PR.

## Related Files

- `configs/news_sources.yml` — source of truth.
- `Backend/app/models/news_sources.py` — loader + validation.
- `Backend/scripts/news_sources_check.py` — CLI reader for workers and CI.
- `Backend/tests/test_news_sources.py` — loader regression tests.


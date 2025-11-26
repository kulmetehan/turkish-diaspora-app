# News Cities Registry

The Turkish Diaspora news experience relies on a single hand-managed YAML file –
`configs/news_cities_template.yml` – to describe every supported city,
district, or province across NL (gemeenten) and TR (iller + ilçeler).

## File layout

- `version`: semantic bump whenever the schema changes.
- `defaults`: optional per-country list of `city_key` values used for
  recommended chips and Google News source bootstrapping.
- `cities`: ordered array of records containing:
  - `city_key`: lowercase slug with country prefix  
    (`nl-rotterdam`, `tr-ankara-çankaya`).
  - `name`: human-readable label (keep diacritics).
  - `country`: `NL` or `TR`.
  - `province`: NL provincie or TR il (nullable).
  - `parent_key`: nullable reference that enables TR hierarchies (il → ilçe).
  - Optional metadata (population, `lat`/`lng`, `metadata.google_news_query`,
    `metadata.legacy_key` for backwards compatibility).

See the sample entries inside the YAML for formatting guidance.

## Workflow

1. **Edit** `configs/news_cities_template.yml` manually to add/update cities.  
   Do not introduce a database table or UI – this file remains the canonical
   source.
2. **Commit & push** the changes along with any related code.
3. **Reload / redeploy** the backend so the FastAPI process can re-read the
   YAML (the loader watches the file mtime, but a restart is required in
   production environments).
4. The backend automatically exposes the data via:
   - `GET /api/v1/news/cities?country=nl|tr` – full list (with optional filter).
   - `GET /api/v1/news/cities/search?country=...&q=...` – substring/prefix search.
5. The frontend city selector consumes the same API responses; no additional
   admin UI is needed.

## Tips for contributors

- Keep the list alphabetized per country and ensure every `parent_key`
  references an existing record.
- Provide `metadata.google_news_query` so dynamic Google News sources inherit
  precise queries.
- Add `metadata.legacy_key` when a historical identifier (e.g. `den_haag`)
  differs from the new slug (`nl-den-haag`); this preserves compatibility with
  existing tagging data.
- If the file size approaches ~1 MB, consider breaking it into country-specific
  includes, but YAML remains acceptable for the foreseeable future.


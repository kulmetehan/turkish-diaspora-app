from app.models.news_city_config import (
    get_city_config,
    get_city_google_news_query,
    get_default_cities,
    list_news_cities,
    search_news_cities,
)


_SAMPLE_CONFIG = """
version: 1
defaults:
  nl:
    - nl-rotterdam
  tr:
    - tr-istanbul
cities:
  - city_key: nl-rotterdam
    name: Rotterdam
    country: NL
    province: Zuid-Holland
    metadata:
      legacy_key: rotterdam
      google_news_query: "Rotterdam Custom Query"
  - city_key: nl-utrecht
    name: Utrecht
    country: NL
    province: Utrecht
    metadata:
      legacy_key: utrecht
  - city_key: tr-istanbul
    name: İstanbul
    country: TR
    province: İstanbul
    metadata:
      legacy_key: istanbul
  - city_key: tr-izmir
    name: İzmir
    country: TR
    province: İzmir
    metadata:
      legacy_key: izmir
"""


def test_get_city_config_returns_all_entries(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    catalog = get_city_config(path)
    assert len(catalog["nl"]) == 2
    assert catalog["nl"][0].city_key == "nl-rotterdam"
    assert len(catalog["tr"]) == 2


def test_get_default_cities_respects_defaults(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    defaults = get_default_cities(path)
    assert [city.city_key for city in defaults["nl"]] == ["nl-rotterdam"]
    assert [city.city_key for city in defaults["tr"]] == ["tr-istanbul"]


def test_search_news_cities_matches_by_name(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    matches = search_news_cities("nl", "utr", path=path)
    assert len(matches) == 1
    assert matches[0].city_key == "nl-utrecht"

    matches_tr = search_news_cities("tr", "İz", path=path)
    assert len(matches_tr) == 1
    assert matches_tr[0].city_key == "tr-izmir"


def test_list_news_cities_supports_country_filter(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    all_cities = list_news_cities(path=path)
    assert len(all_cities) == 4

    nl_cities = list_news_cities(country="nl", path=path)
    assert [city.city_key for city in nl_cities] == ["nl-rotterdam", "nl-utrecht"]


def test_get_city_google_news_query_prefers_metadata(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    query = get_city_google_news_query("nl-rotterdam", path=path)
    assert query == "Rotterdam Custom Query"


def test_get_city_google_news_query_fallbacks_by_country(tmp_path):
    path = tmp_path / "cities.yml"
    path.write_text(_SAMPLE_CONFIG, encoding="utf-8")

    tr_query = get_city_google_news_query("tr-izmir", path=path)
    assert tr_query == "İzmir Türkiye"

    missing_query = get_city_google_news_query("unknown-city", path=path)
    assert missing_query == "unknown-city"

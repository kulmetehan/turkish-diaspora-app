from __future__ import annotations

from pathlib import Path

import pytest

from app.models import news_city_tags as city_tags


@pytest.fixture(autouse=True)
def _reset_cache():
    city_tags.clear_city_tags_cache()
    yield
    city_tags.clear_city_tags_cache()


def _write_config(path: Path, body: str) -> None:
    path.write_text(body.strip() + "\n", encoding="utf-8")


def test_get_aliases_returns_normalized_map(tmp_path: Path):
    cfg = tmp_path / "news_city_tags.yml"
    _write_config(
        cfg,
        """
        version: 1
        nl:
          - city_key: rotterdam
            city_name: "Rotterdam"
            aliases:
              - Rotterdam
              - R'dam
        tr:
          - city_key: istanbul
            city_name: "İstanbul"
            aliases:
              - İstanbul
        """,
    )

    aliases = city_tags.get_aliases("nl", path=cfg)
    assert "rotterdam" in aliases
    assert "r'dam" not in aliases  # normalized removes punctuation
    assert "r dam" in aliases
    assert aliases["rotterdam"].city_key == "rotterdam"
    assert aliases["rotterdam"].country == "nl"


def test_match_city_prefers_requested_country(tmp_path: Path):
    cfg = tmp_path / "news_city_tags.yml"
    _write_config(
        cfg,
        """
        version: 1
        nl:
          - city_key: amsterdam
            city_name: "Amsterdam"
            aliases: ["Amsterdam"]
        tr:
          - city_key: ankara
            city_name: "Ankara"
            aliases: ["Ankara"]
        """,
    )

    text = "De burgemeester van Amsterdam bezocht Ankara gisteren."
    match_nl = city_tags.match_city(text, countries=["nl"], path=cfg)
    assert match_nl is not None
    assert match_nl.city_key == "amsterdam"

    match_tr = city_tags.match_city(text, countries=["tr"], path=cfg)
    assert match_tr is not None
    assert match_tr.city_key == "ankara"


def test_missing_file_returns_empty_aliases(tmp_path: Path):
    cfg = tmp_path / "missing.yml"
    aliases = city_tags.get_aliases("nl", path=cfg)
    assert aliases == {}
    assert city_tags.match_city("Example text", path=cfg) is None





import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate_google_to_osm.py"
SPEC = importlib.util.spec_from_file_location("migrate_google_to_osm", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None  # pragma: no cover - defensive sanity
SPEC.loader.exec_module(MODULE)


normalize_name = MODULE.normalize_name
similarity_ratio = MODULE.similarity_ratio


def test_normalize_name_basic():
    assert normalize_name("  Ankara   Market  ") == "ankara market"
    assert normalize_name(None) == ""
    assert normalize_name("  ") == ""


def test_similarity_identical_names():
    score = similarity_ratio("Istanbul Bakery", "istanbul bakery")
    assert score == 1.0


def test_similarity_minor_variations():
    score = similarity_ratio("Göreme Kebab House", "Goreme kebab-house ")
    assert score >= 0.9


def test_similarity_different_names():
    score = similarity_ratio("Izmir Lokanta", "Eindhoven Market")
    assert score < 0.5


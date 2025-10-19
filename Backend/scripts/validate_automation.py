#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_automation.py
Validateert of de automation-run matrix klopt met de configuratie:
- Vereiste categorieën bestaan in Infra/config/categories.yml en hebben geldige google_types
- Opgegeven stad (default: rotterdam) bestaat in Infra/config/cities.yml met >= min_districts

Gebruik:
  cd Backend
  source .venv/bin/activate
  python scripts/validate_automation.py \
      --categories bakery,restaurant,supermarket,barber,mosque,travel_agency \
      --city rotterdam --min-districts 5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("❌ PyYAML is niet geïnstalleerd. Voer uit: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def repo_root_from_here() -> Path:
    # Dit script staat in Backend/scripts → repo-root is 2 niveaus omhoog
    here = Path(__file__).resolve()
    return here.parents[2]


def load_yaml(p: Path) -> dict:
    if not p.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {p}")
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise RuntimeError(f"YAML laadfout voor {p}: {e}") from e


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validatie voor geautomatiseerde categorie-runs.")
    ap.add_argument(
        "--categories",
        help="Komma-gescheiden lijst van vereiste categorieën (default matrix van workflow).",
        default="bakery,restaurant,supermarket,barber,mosque,travel_agency",
    )
    ap.add_argument("--city", default="rotterdam", help="Stad die aanwezig moet zijn (default: rotterdam).")
    ap.add_argument("--min-districts", type=int, default=5, help="Minimaal aantal districten (default: 5).")
    return ap.parse_args()


def validate_categories(cfg: dict, required: list[str]) -> None:
    cats = cfg.get("categories")
    if not isinstance(cats, dict) or not cats:
        raise SystemExit("❌ Ongeldig: 'categories' root ontbreekt of is leeg in Infra/config/categories.yml")

    missing = [c for c in required if c not in cats]
    if missing:
        raise SystemExit(f"❌ Ontbrekende categorieën in categories.yml: {missing}")

    # Basis sanity per categorie
    for k in required:
        node = cats.get(k) or {}
        gt = node.get("google_types")
        if not isinstance(gt, list) or not all(isinstance(x, str) and x.strip() for x in gt):
            raise SystemExit(f"❌ Categorie '{k}' heeft ongeldige of lege 'google_types' in categories.yml")


def validate_cities(cfg: dict, city_key: str, min_districts: int) -> None:
    cities = cfg.get("cities")
    if not isinstance(cities, dict) or not cities:
        raise SystemExit("❌ Ongeldig: 'cities' root ontbreekt of is leeg in Infra/config/cities.yml")

    city = cities.get(city_key)
    if not isinstance(city, dict):
        raise SystemExit(f"❌ Stad '{city_key}' ontbreekt in Infra/config/cities.yml")

    districts = city.get("districts")
    if not isinstance(districts, dict) or len(districts) < min_districts:
        raise SystemExit(
            f"❌ Stad '{city_key}' heeft onvoldoende districten: {0 if not isinstance(districts, dict) else len(districts)} "
            f"(minimaal vereist: {min_districts})"
        )

    # Minimale bbox controle
    required_keys = {"lat_min", "lat_max", "lng_min", "lng_max"}
    for name, bbox in districts.items():
        if not isinstance(bbox, dict) or not required_keys.issubset(bbox.keys()):
            raise SystemExit(f"❌ District '{name}' mist bbox keys {required_keys}")
        try:
            latmin, latmax = float(bbox["lat_min"]), float(bbox["lat_max"])
            lngmin, lngmax = float(bbox["lng_min"]), float(bbox["lng_max"])
        except Exception:
            raise SystemExit(f"❌ District '{name}' bbox bevat non-numerieke waarden")
        if not (-90.0 <= latmin < latmax <= 90.0):
            raise SystemExit(f"❌ District '{name}' ongeldige latitude-range: {latmin}..{latmax}")
        if not (-180.0 <= lngmin < lngmax <= 180.0):
            raise SystemExit(f"❌ District '{name}' ongeldige longitude-range: {lngmin}..{lngmax}")


def main() -> None:
    args = parse_args()

    root = repo_root_from_here()
    cats_path = root / "Infra" / "config" / "categories.yml"
    cities_path = root / "Infra" / "config" / "cities.yml"

    cats_cfg = load_yaml(cats_path)
    cities_cfg = load_yaml(cities_path)

    required_categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if not required_categories:
        raise SystemExit("❌ Geen categorieën opgegeven via --categories")

    validate_categories(cats_cfg, required_categories)
    validate_cities(cities_cfg, args.city, args.min_districts)

    print("✅ All categories configured")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # SystemExit met custom message al geprint; exit met code 1 als het een fout is
        code = 0 if str(e) == "" else 1
        sys.exit(code)
    except KeyboardInterrupt:
        print("❌ Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Onverwachte fout: {e}", file=sys.stderr)
        sys.exit(1)

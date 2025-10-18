#!/usr/bin/env python3
"""
validate_city_grid.py
Validate /Infra/config/cities.yml structure & value ranges.

Usage:
  cd Backend
  source .venv/bin/activate
  python scripts/validate_city_grid.py --file ../Infra/config/cities.yml
"""
import sys
import argparse
import yaml

def validate_bbox(name, d):
    required = ["lat_min","lat_max","lng_min","lng_max"]
    for k in required:
        if k not in d:
            raise ValueError(f"[{name}] missing key: {k}")
        if not isinstance(d[k], (int, float)):
            raise ValueError(f"[{name}] {k} must be number")
    if not ( -90.0 <= d["lat_min"] < d["lat_max"] <= 90.0 ):
        raise ValueError(f"[{name}] invalid lat range")
    if not ( -180.0 <= d["lng_min"] < d["lng_max"] <= 180.0 ):
        raise ValueError(f"[{name}] invalid lng range")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if "cities" not in cfg or "rotterdam" not in cfg["cities"]:
        raise SystemExit("rotterdam config not found under 'cities'")

    rdam = cfg["cities"]["rotterdam"]
    districts = rdam.get("districts", {})
    if not isinstance(districts, dict) or len(districts) < 5:
        raise SystemExit("need at least 5 districts for rotterdam")

    for key, bbox in districts.items():
        validate_bbox(f"rotterdam.{key}", bbox)

    print("✅ YAML valid")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        sys.exit(1)

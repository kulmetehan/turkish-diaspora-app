#!/usr/bin/env python3
"""
validate_categories.py
Sneltest voor /Infra/config/categories.yml

Usage:
  cd Backend
  source .venv/bin/activate
  python scripts/validate_categories.py --file ../Infra/config/categories.yml
"""
import argparse
import sys
import yaml

BAD_TYPES = {"grocery_or_supermarket"}  # vul aan indien nodig

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "categories" not in data:
        raise SystemExit("❌ Ongeldig: root 'categories' ontbreekt.")

    cats = data["categories"]
    if not isinstance(cats, dict) or not cats:
        raise SystemExit("❌ Ongeldig: 'categories' moet een niet-lege mapping zijn.")

    for k, v in cats.items():
        g = (v or {}).get("google_types")
        if not isinstance(g, list) or not all(isinstance(x, str) and x.strip() for x in g):
            raise SystemExit(f"❌ Ongeldig: categorie '{k}' heeft ongeldige 'google_types'.")

        bad = [x for x in g if x in BAD_TYPES]
        if bad:
            raise SystemExit(f"❌ Ongeldig: categorie '{k}' bevat verboden types: {bad}")

    print("✅ categories.yml valid")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env bash
set -euo pipefail

# 1) Zorg dat we in de juiste map staan
cd "$(dirname "$0")"  # gaat naar Backend/

# 2) Maak een dedicated virtualenv (vermijdt PEP 668)
python -m venv .venv

# 3) Activeer venv en installeer requirements
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt

# 4) (optioneel) print python & pip versies ter debug
python --version
pip --version

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"  # naar Backend/
source .venv/bin/activate

# Render zet $PORT voor je; val terug op 8000 voor lokale runs
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

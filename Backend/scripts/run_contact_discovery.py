#!/usr/bin/env python3
"""
CLI script to run the contact discovery bot.

Usage:
    python scripts/run_contact_discovery.py [--batch-size 100] [--max-locations 1000] [--worker-run-id UUID]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add Backend to path
THIS_FILE = Path(__file__).resolve()
BACKEND_DIR = THIS_FILE.parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import and run main
from app.workers.contact_discovery_bot import main

if __name__ == "__main__":
    main()


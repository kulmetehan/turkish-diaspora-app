#!/usr/bin/env python3
"""
CLI script to run the outreach mailer bot.

Usage:
    python scripts/run_outreach_mailer.py [--batch-size 50] [--sleep-interval 60] [--max-iterations 10]
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
from app.workers.outreach_mailer_bot import main

if __name__ == "__main__":
    main()


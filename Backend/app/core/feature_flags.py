# Backend/app/core/feature_flags.py
from __future__ import annotations

import os
from typing import Dict


FEATURE_FLAGS: Dict[str, bool] = {
    "check_ins_enabled": os.getenv("FEATURE_CHECK_INS", "false").lower() == "true",
    "polls_enabled": os.getenv("FEATURE_POLLS", "false").lower() == "true",
    "trending_enabled": os.getenv("FEATURE_TRENDING", "false").lower() == "true",
    "gamification_enabled": os.getenv("FEATURE_GAMIFICATION", "false").lower() == "true",
    "business_accounts_enabled": os.getenv("FEATURE_BUSINESS", "false").lower() == "true",
    "reactions_enabled": os.getenv("FEATURE_REACTIONS", "false").lower() == "true",
    "notes_enabled": os.getenv("FEATURE_NOTES", "false").lower() == "true",
}


def require_feature(feature_name: str) -> None:
    """Raise 501 if feature is disabled."""
    if not FEATURE_FLAGS.get(feature_name, False):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=501,
            detail=f"Feature '{feature_name}' is not enabled"
        )
















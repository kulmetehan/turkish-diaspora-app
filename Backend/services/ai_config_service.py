from __future__ import annotations

import os
from typing import Optional, Any, Mapping
from datetime import datetime

from services.db_service import fetch, fetchrow, execute
from app.models.ai_config import AIConfig, AIConfigUpdate
from app.core.logging import get_logger

logger = get_logger()

NEWS_THRESHOLD_DEFAULTS = {
    "news_diaspora_min_score": 0.75,
    "news_nl_min_score": 0.75,
    "news_tr_min_score": 0.75,
    "news_local_min_score": 0.70,
    "news_origin_min_score": 0.70,
    "news_geo_min_score": 0.80,
}


def _float_with_default(value: Optional[float], default: float) -> float:
    return float(value) if value is not None else default


def _build_config_from_row(row: Mapping[str, Any]) -> AIConfig:
    data = dict(row)
    return AIConfig(
        id=int(data["id"]),
        classify_min_conf=float(data["classify_min_conf"]),
        verify_min_conf=float(data["verify_min_conf"]),
        task_verifier_min_conf=float(data["task_verifier_min_conf"]),
        auto_promote_conf=float(data["auto_promote_conf"]),
        news_diaspora_min_score=_float_with_default(data.get("news_diaspora_min_score"), NEWS_THRESHOLD_DEFAULTS["news_diaspora_min_score"]),
        news_nl_min_score=_float_with_default(data.get("news_nl_min_score"), NEWS_THRESHOLD_DEFAULTS["news_nl_min_score"]),
        news_tr_min_score=_float_with_default(data.get("news_tr_min_score"), NEWS_THRESHOLD_DEFAULTS["news_tr_min_score"]),
        news_local_min_score=_float_with_default(data.get("news_local_min_score"), NEWS_THRESHOLD_DEFAULTS["news_local_min_score"]),
        news_origin_min_score=_float_with_default(data.get("news_origin_min_score"), NEWS_THRESHOLD_DEFAULTS["news_origin_min_score"]),
        news_geo_min_score=_float_with_default(data.get("news_geo_min_score"), NEWS_THRESHOLD_DEFAULTS["news_geo_min_score"]),
        monitor_low_conf_days=int(data["monitor_low_conf_days"]),
        monitor_medium_conf_days=int(data["monitor_medium_conf_days"]),
        monitor_high_conf_days=int(data["monitor_high_conf_days"]),
        monitor_verified_few_reviews_days=int(data["monitor_verified_few_reviews_days"]),
        monitor_verified_medium_reviews_days=int(data["monitor_verified_medium_reviews_days"]),
        monitor_verified_many_reviews_days=int(data["monitor_verified_many_reviews_days"]),
        updated_at=data["updated_at"],
        updated_by=data.get("updated_by"),
    )


async def get_ai_config() -> Optional[AIConfig]:
    """
    Fetch current AI config from database.
    Returns None if config table is not initialized.
    """
    sql = """
        SELECT 
            id,
            classify_min_conf,
            verify_min_conf,
            task_verifier_min_conf,
            auto_promote_conf,
            news_diaspora_min_score,
            news_nl_min_score,
            news_tr_min_score,
            news_local_min_score,
            news_origin_min_score,
            news_geo_min_score,
            monitor_low_conf_days,
            monitor_medium_conf_days,
            monitor_high_conf_days,
            monitor_verified_few_reviews_days,
            monitor_verified_medium_reviews_days,
            monitor_verified_many_reviews_days,
            updated_at,
            updated_by
        FROM ai_config
        WHERE id = 1
    """
    row = await fetchrow(sql)
    if not row:
        return None
    
    return _build_config_from_row(row)


async def initialize_ai_config() -> AIConfig:
    """
    Initialize ai_config table with default values if missing (idempotent).
    Returns the current config (either existing or newly created).
    """
    # Try to get existing config first
    existing = await get_ai_config()
    if existing:
        return existing
    
    # Initialize with defaults
    sql = """
        INSERT INTO ai_config (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING
        RETURNING 
            id,
            classify_min_conf,
            verify_min_conf,
            task_verifier_min_conf,
            auto_promote_conf,
            news_diaspora_min_score,
            news_nl_min_score,
            news_tr_min_score,
            news_local_min_score,
            news_origin_min_score,
            news_geo_min_score,
            monitor_low_conf_days,
            monitor_medium_conf_days,
            monitor_high_conf_days,
            monitor_verified_few_reviews_days,
            monitor_verified_medium_reviews_days,
            monitor_verified_many_reviews_days,
            updated_at,
            updated_by
    """
    row = await fetchrow(sql)
    
    # If still None (race condition), fetch again
    if not row:
        existing = await get_ai_config()
        if existing:
            return existing
        raise RuntimeError("Failed to initialize ai_config table")
    
    return _build_config_from_row(row)


async def update_ai_config(update: AIConfigUpdate, updated_by: str) -> AIConfig:
    """
    Update AI config with provided values.
    Logs old vs new values for audit trail.
    """
    # Get current config for logging
    current = await get_ai_config()
    if not current:
        current = await initialize_ai_config()
    
    # Build update SQL dynamically based on provided fields
    updates = []
    params = []
    param_idx = 1
    
    if update.classify_min_conf is not None:
        updates.append(f"classify_min_conf = ${param_idx}")
        params.append(float(update.classify_min_conf))
        param_idx += 1
    
    if update.verify_min_conf is not None:
        updates.append(f"verify_min_conf = ${param_idx}")
        params.append(float(update.verify_min_conf))
        param_idx += 1
    
    if update.task_verifier_min_conf is not None:
        updates.append(f"task_verifier_min_conf = ${param_idx}")
        params.append(float(update.task_verifier_min_conf))
        param_idx += 1
    
    if update.auto_promote_conf is not None:
        updates.append(f"auto_promote_conf = ${param_idx}")
        params.append(float(update.auto_promote_conf))
        param_idx += 1

    if update.news_diaspora_min_score is not None:
        updates.append(f"news_diaspora_min_score = ${param_idx}")
        params.append(float(update.news_diaspora_min_score))
        param_idx += 1

    if update.news_nl_min_score is not None:
        updates.append(f"news_nl_min_score = ${param_idx}")
        params.append(float(update.news_nl_min_score))
        param_idx += 1

    if update.news_tr_min_score is not None:
        updates.append(f"news_tr_min_score = ${param_idx}")
        params.append(float(update.news_tr_min_score))
        param_idx += 1

    if update.news_local_min_score is not None:
        updates.append(f"news_local_min_score = ${param_idx}")
        params.append(float(update.news_local_min_score))
        param_idx += 1

    if update.news_origin_min_score is not None:
        updates.append(f"news_origin_min_score = ${param_idx}")
        params.append(float(update.news_origin_min_score))
        param_idx += 1

    if update.news_geo_min_score is not None:
        updates.append(f"news_geo_min_score = ${param_idx}")
        params.append(float(update.news_geo_min_score))
        param_idx += 1
    
    if update.monitor_low_conf_days is not None:
        updates.append(f"monitor_low_conf_days = ${param_idx}")
        params.append(int(update.monitor_low_conf_days))
        param_idx += 1
    
    if update.monitor_medium_conf_days is not None:
        updates.append(f"monitor_medium_conf_days = ${param_idx}")
        params.append(int(update.monitor_medium_conf_days))
        param_idx += 1
    
    if update.monitor_high_conf_days is not None:
        updates.append(f"monitor_high_conf_days = ${param_idx}")
        params.append(int(update.monitor_high_conf_days))
        param_idx += 1
    
    if update.monitor_verified_few_reviews_days is not None:
        updates.append(f"monitor_verified_few_reviews_days = ${param_idx}")
        params.append(int(update.monitor_verified_few_reviews_days))
        param_idx += 1
    
    if update.monitor_verified_medium_reviews_days is not None:
        updates.append(f"monitor_verified_medium_reviews_days = ${param_idx}")
        params.append(int(update.monitor_verified_medium_reviews_days))
        param_idx += 1
    
    if update.monitor_verified_many_reviews_days is not None:
        updates.append(f"monitor_verified_many_reviews_days = ${param_idx}")
        params.append(int(update.monitor_verified_many_reviews_days))
        param_idx += 1
    
    if not updates:
        # No changes, return current config
        return current
    
    # Add updated_at and updated_by
    updates.append(f"updated_at = ${param_idx}")
    params.append(datetime.utcnow())
    param_idx += 1
    
    updates.append(f"updated_by = ${param_idx}")
    params.append(updated_by)
    
    # Build and execute update
    sql = f"""
        UPDATE ai_config
        SET {', '.join(updates)}
        WHERE id = 1
        RETURNING 
            id,
            classify_min_conf,
            verify_min_conf,
            task_verifier_min_conf,
            auto_promote_conf,
            news_diaspora_min_score,
            news_nl_min_score,
            news_tr_min_score,
            news_local_min_score,
            news_origin_min_score,
            news_geo_min_score,
            monitor_low_conf_days,
            monitor_medium_conf_days,
            monitor_high_conf_days,
            monitor_verified_few_reviews_days,
            monitor_verified_medium_reviews_days,
            monitor_verified_many_reviews_days,
            updated_at,
            updated_by
    """
    
    row = await fetchrow(sql, *params)
    if not row:
        raise RuntimeError("Failed to update ai_config")
    
    updated = _build_config_from_row(row)
    
    # Log changes for audit
    changes = []
    if update.classify_min_conf is not None and current.classify_min_conf != updated.classify_min_conf:
        changes.append(f"classify_min_conf: {current.classify_min_conf} -> {updated.classify_min_conf}")
    if update.verify_min_conf is not None and current.verify_min_conf != updated.verify_min_conf:
        changes.append(f"verify_min_conf: {current.verify_min_conf} -> {updated.verify_min_conf}")
    if update.task_verifier_min_conf is not None and current.task_verifier_min_conf != updated.task_verifier_min_conf:
        changes.append(f"task_verifier_min_conf: {current.task_verifier_min_conf} -> {updated.task_verifier_min_conf}")
    if update.auto_promote_conf is not None and current.auto_promote_conf != updated.auto_promote_conf:
        changes.append(f"auto_promote_conf: {current.auto_promote_conf} -> {updated.auto_promote_conf}")
    if update.news_diaspora_min_score is not None and current.news_diaspora_min_score != updated.news_diaspora_min_score:
        changes.append(f"news_diaspora_min_score: {current.news_diaspora_min_score} -> {updated.news_diaspora_min_score}")
    if update.news_nl_min_score is not None and current.news_nl_min_score != updated.news_nl_min_score:
        changes.append(f"news_nl_min_score: {current.news_nl_min_score} -> {updated.news_nl_min_score}")
    if update.news_tr_min_score is not None and current.news_tr_min_score != updated.news_tr_min_score:
        changes.append(f"news_tr_min_score: {current.news_tr_min_score} -> {updated.news_tr_min_score}")
    if update.news_local_min_score is not None and current.news_local_min_score != updated.news_local_min_score:
        changes.append(f"news_local_min_score: {current.news_local_min_score} -> {updated.news_local_min_score}")
    if update.news_origin_min_score is not None and current.news_origin_min_score != updated.news_origin_min_score:
        changes.append(f"news_origin_min_score: {current.news_origin_min_score} -> {updated.news_origin_min_score}")
    if update.news_geo_min_score is not None and current.news_geo_min_score != updated.news_geo_min_score:
        changes.append(f"news_geo_min_score: {current.news_geo_min_score} -> {updated.news_geo_min_score}")
    if update.monitor_low_conf_days is not None and current.monitor_low_conf_days != updated.monitor_low_conf_days:
        changes.append(f"monitor_low_conf_days: {current.monitor_low_conf_days} -> {updated.monitor_low_conf_days}")
    if update.monitor_medium_conf_days is not None and current.monitor_medium_conf_days != updated.monitor_medium_conf_days:
        changes.append(f"monitor_medium_conf_days: {current.monitor_medium_conf_days} -> {updated.monitor_medium_conf_days}")
    if update.monitor_high_conf_days is not None and current.monitor_high_conf_days != updated.monitor_high_conf_days:
        changes.append(f"monitor_high_conf_days: {current.monitor_high_conf_days} -> {updated.monitor_high_conf_days}")
    if update.monitor_verified_few_reviews_days is not None and current.monitor_verified_few_reviews_days != updated.monitor_verified_few_reviews_days:
        changes.append(f"monitor_verified_few_reviews_days: {current.monitor_verified_few_reviews_days} -> {updated.monitor_verified_few_reviews_days}")
    if update.monitor_verified_medium_reviews_days is not None and current.monitor_verified_medium_reviews_days != updated.monitor_verified_medium_reviews_days:
        changes.append(f"monitor_verified_medium_reviews_days: {current.monitor_verified_medium_reviews_days} -> {updated.monitor_verified_medium_reviews_days}")
    if update.monitor_verified_many_reviews_days is not None and current.monitor_verified_many_reviews_days != updated.monitor_verified_many_reviews_days:
        changes.append(f"monitor_verified_many_reviews_days: {current.monitor_verified_many_reviews_days} -> {updated.monitor_verified_many_reviews_days}")
    
    if changes:
        logger.info(
            "ai_config_updated",
            updated_by=updated_by,
            changes=changes,
        )
    
    return updated


async def get_threshold_for_bot(bot_name: str) -> Optional[float]:
    """
    Get threshold for a specific bot from config, with fallback to env vars.
    Returns None if config not available and no env var set (caller should use hard-coded default).
    
    Bot name mapping:
    - "classify_bot" -> classify_min_conf
    - "verify_locations" -> verify_min_conf
    - "task_verifier" -> task_verifier_min_conf
    """
    config = await get_ai_config()
    
    if bot_name == "classify_bot":
        if config:
            return config.classify_min_conf
        # Fallback to env var
        env_val = os.getenv("CLASSIFY_MIN_CONF")
        return float(env_val) if env_val else None
    
    elif bot_name == "verify_locations":
        if config:
            return config.verify_min_conf
        # No env var for verify_locations, return None for hard-coded default
        return None
    
    elif bot_name == "task_verifier":
        if config:
            return config.task_verifier_min_conf
        # No env var for task_verifier, return None for hard-coded default
        return None
    
    return None


async def get_auto_promote_conf() -> Optional[float]:
    """
    Get auto-promotion threshold from config.
    Returns None if config not available (caller should use hard-coded default 0.90).
    """
    config = await get_ai_config()
    if config:
        return config.auto_promote_conf
    return None













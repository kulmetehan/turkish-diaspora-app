from __future__ import annotations

import os
from typing import Optional
from datetime import datetime

from services.db_service import fetch, fetchrow, execute
from app.models.ai_config import AIConfig, AIConfigUpdate
from app.core.logging import get_logger

logger = get_logger()


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
    
    return AIConfig(
        id=int(row["id"]),
        classify_min_conf=float(row["classify_min_conf"]),
        verify_min_conf=float(row["verify_min_conf"]),
        task_verifier_min_conf=float(row["task_verifier_min_conf"]),
        auto_promote_conf=float(row["auto_promote_conf"]),
        monitor_low_conf_days=int(row["monitor_low_conf_days"]),
        monitor_medium_conf_days=int(row["monitor_medium_conf_days"]),
        monitor_high_conf_days=int(row["monitor_high_conf_days"]),
        monitor_verified_few_reviews_days=int(row["monitor_verified_few_reviews_days"]),
        monitor_verified_medium_reviews_days=int(row["monitor_verified_medium_reviews_days"]),
        monitor_verified_many_reviews_days=int(row["monitor_verified_many_reviews_days"]),
        updated_at=row["updated_at"],
        updated_by=row.get("updated_by"),
    )


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
    
    return AIConfig(
        id=int(row["id"]),
        classify_min_conf=float(row["classify_min_conf"]),
        verify_min_conf=float(row["verify_min_conf"]),
        task_verifier_min_conf=float(row["task_verifier_min_conf"]),
        auto_promote_conf=float(row["auto_promote_conf"]),
        monitor_low_conf_days=int(row["monitor_low_conf_days"]),
        monitor_medium_conf_days=int(row["monitor_medium_conf_days"]),
        monitor_high_conf_days=int(row["monitor_high_conf_days"]),
        monitor_verified_few_reviews_days=int(row["monitor_verified_few_reviews_days"]),
        monitor_verified_medium_reviews_days=int(row["monitor_verified_medium_reviews_days"]),
        monitor_verified_many_reviews_days=int(row["monitor_verified_many_reviews_days"]),
        updated_at=row["updated_at"],
        updated_by=row.get("updated_by"),
    )


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
    
    updated = AIConfig(
        id=int(row["id"]),
        classify_min_conf=float(row["classify_min_conf"]),
        verify_min_conf=float(row["verify_min_conf"]),
        task_verifier_min_conf=float(row["task_verifier_min_conf"]),
        auto_promote_conf=float(row["auto_promote_conf"]),
        monitor_low_conf_days=int(row["monitor_low_conf_days"]),
        monitor_medium_conf_days=int(row["monitor_medium_conf_days"]),
        monitor_high_conf_days=int(row["monitor_high_conf_days"]),
        monitor_verified_few_reviews_days=int(row["monitor_verified_few_reviews_days"]),
        monitor_verified_medium_reviews_days=int(row["monitor_verified_medium_reviews_days"]),
        monitor_verified_many_reviews_days=int(row["monitor_verified_many_reviews_days"]),
        updated_at=row["updated_at"],
        updated_by=row.get("updated_by"),
    )
    
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





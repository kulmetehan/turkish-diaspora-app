"""
Categories Database Service - Manages categories configuration in database.

This service provides database-driven access to categories configuration, replacing
the YAML-based approach to avoid synchronization issues and enable dynamic management.

All functions maintain backwards compatibility with the YAML structure format.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from services.db_service import fetch, fetchrow, execute, init_db_pool
from app.core.logging import get_logger
from app.workers.discovery_bot import CATEGORIES_YML

logger = get_logger()


def _load_defaults_from_yaml() -> Dict[str, Any]:
    """Load defaults section from YAML file (still using YAML for defaults)."""
    try:
        if CATEGORIES_YML.exists():
            import yaml
            data = yaml.safe_load(CATEGORIES_YML.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("defaults", {})
    except Exception as e:
        logger.warning("failed_to_load_defaults_from_yaml", error=str(e))
    return {}


async def load_categories_config_from_db() -> Dict[str, Any]:
    """
    Load all categories from database.
    
    Returns same dict structure as YAML loader for backwards compatibility:
    {
        "version": 1,
        "defaults": {...},  # From YAML (still using YAML for defaults)
        "categories": {
            "category_key": {
                "label": "...",
                "description": "...",
                "aliases": [...],
                "google_types": [...],
                "osm_tags": {...},
                "discovery": {
                    "enabled": true,
                    "priority": 10,
                    "strategy": null,
                    "max_per_cell": null
                }
            }
        }
    }
    """
    await init_db_pool()
    
    try:
        # Load all categories
        categories_sql = """
            SELECT 
                category_key,
                label,
                description,
                aliases,
                google_types,
                osm_tags,
                discovery_enabled,
                discovery_priority,
                discovery_strategy,
                discovery_max_per_cell
            FROM categories_config
            ORDER BY category_key ASC
        """
        categories_rows = await fetch(categories_sql)
        
        if not categories_rows:
            logger.warning("no_categories_in_database")
            return {
                "version": 1,
                "defaults": _load_defaults_from_yaml(),
                "categories": {}
            }
        
        # Build categories dict
        categories_dict: Dict[str, Any] = {}
        
        for row in categories_rows:
            category_key = row["category_key"]
            
            # Parse JSONB fields
            aliases = row.get("aliases") or []
            if isinstance(aliases, str):
                try:
                    aliases = json.loads(aliases)
                except Exception:
                    aliases = []
            
            google_types = row.get("google_types") or []
            if isinstance(google_types, str):
                try:
                    google_types = json.loads(google_types)
                except Exception:
                    google_types = []
            
            osm_tags = row.get("osm_tags")
            if isinstance(osm_tags, str):
                try:
                    osm_tags = json.loads(osm_tags)
                except Exception:
                    osm_tags = None
            
            # Build discovery config
            discovery_cfg: Dict[str, Any] = {
                "enabled": bool(row.get("discovery_enabled", True)),
                "priority": int(row.get("discovery_priority", 0)),
            }
            
            if row.get("discovery_strategy"):
                discovery_cfg["strategy"] = str(row["discovery_strategy"])
            
            if row.get("discovery_max_per_cell") is not None:
                discovery_cfg["max_per_cell"] = int(row["discovery_max_per_cell"])
            
            categories_dict[category_key] = {
                "label": row["label"],
                "description": row.get("description") or "",
                "aliases": aliases if isinstance(aliases, list) else [],
                "google_types": google_types if isinstance(google_types, list) else [],
                "osm_tags": osm_tags,
                "discovery": discovery_cfg,
            }
        
        return {
            "version": 1,
            "defaults": _load_defaults_from_yaml(),
            "categories": categories_dict
        }
        
    except Exception as e:
        logger.error("failed_to_load_categories_from_database", error=str(e), exc_info=e)
        raise


async def get_category_from_db(category_key: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific category from database.
    
    Returns category dict with same structure as YAML, or None if not found.
    """
    await init_db_pool()
    
    sql = """
        SELECT 
            category_key,
            label,
            description,
            aliases,
            google_types,
            osm_tags,
            discovery_enabled,
            discovery_priority,
            discovery_strategy,
            discovery_max_per_cell
        FROM categories_config
        WHERE category_key = $1
    """
    row = await fetchrow(sql, category_key)
    
    if not row:
        return None
    
    # Parse JSONB fields
    aliases = row.get("aliases") or []
    if isinstance(aliases, str):
        try:
            aliases = json.loads(aliases)
        except Exception:
            aliases = []
    
    google_types = row.get("google_types") or []
    if isinstance(google_types, str):
        try:
            google_types = json.loads(google_types)
        except Exception:
            google_types = []
    
    osm_tags = row.get("osm_tags")
    if isinstance(osm_tags, str):
        try:
            osm_tags = json.loads(osm_tags)
        except Exception:
            osm_tags = None
    
    # Build discovery config
    discovery_cfg: Dict[str, Any] = {
        "enabled": bool(row.get("discovery_enabled", True)),
        "priority": int(row.get("discovery_priority", 0)),
    }
    
    if row.get("discovery_strategy"):
        discovery_cfg["strategy"] = str(row["discovery_strategy"])
    
    if row.get("discovery_max_per_cell") is not None:
        discovery_cfg["max_per_cell"] = int(row["discovery_max_per_cell"])
    
    return {
        "label": row["label"],
        "description": row.get("description") or "",
        "aliases": aliases if isinstance(aliases, list) else [],
        "google_types": google_types if isinstance(google_types, list) else [],
        "osm_tags": osm_tags,
        "discovery": discovery_cfg,
    }


async def get_discoverable_categories_from_db() -> List[Dict[str, Any]]:
    """
    Get only discoverable categories from database.
    
    Returns list of category dicts, sorted by discovery_priority (descending).
    """
    await init_db_pool()
    
    sql = """
        SELECT 
            category_key,
            label,
            description,
            aliases,
            google_types,
            osm_tags,
            discovery_enabled,
            discovery_priority,
            discovery_strategy,
            discovery_max_per_cell
        FROM categories_config
        WHERE discovery_enabled = true
        ORDER BY discovery_priority DESC, category_key ASC
    """
    rows = await fetch(sql)
    
    categories = []
    for row in rows:
        category = await get_category_from_db(row["category_key"])
        if category:
            category["key"] = row["category_key"]
            categories.append(category)
    
    return categories


async def save_category_to_db(category_key: str, category_data: Dict[str, Any]) -> None:
    """
    Save category configuration to database (INSERT or UPDATE).
    
    Args:
        category_key: Category key (normalized)
        category_data: Category data dict with label, description, aliases, etc.
    """
    await init_db_pool()
    
    label = category_data.get("label") or category_key
    description = category_data.get("description")
    aliases = category_data.get("aliases", [])
    google_types = category_data.get("google_types", [])
    osm_tags = category_data.get("osm_tags")
    
    discovery_cfg = category_data.get("discovery", {})
    discovery_enabled = discovery_cfg.get("enabled", True)
    discovery_priority = discovery_cfg.get("priority", 0)
    discovery_strategy = discovery_cfg.get("strategy")
    discovery_max_per_cell = discovery_cfg.get("max_per_cell")
    
    sql = """
        INSERT INTO categories_config (
            category_key,
            label,
            description,
            aliases,
            google_types,
            osm_tags,
            discovery_enabled,
            discovery_priority,
            discovery_strategy,
            discovery_max_per_cell,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
        ON CONFLICT (category_key)
        DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description,
            aliases = EXCLUDED.aliases,
            google_types = EXCLUDED.google_types,
            osm_tags = EXCLUDED.osm_tags,
            discovery_enabled = EXCLUDED.discovery_enabled,
            discovery_priority = EXCLUDED.discovery_priority,
            discovery_strategy = EXCLUDED.discovery_strategy,
            discovery_max_per_cell = EXCLUDED.discovery_max_per_cell,
            updated_at = NOW()
    """
    
    await execute(
        sql,
        category_key,
        label,
        description,
        json.dumps(aliases) if aliases else json.dumps([]),
        json.dumps(google_types) if google_types else json.dumps([]),
        json.dumps(osm_tags) if osm_tags else None,
        discovery_enabled,
        discovery_priority,
        discovery_strategy,
        discovery_max_per_cell,
    )
    
    logger.info("category_saved_to_database", category_key=category_key, label=label)


async def delete_category_from_db(category_key: str) -> None:
    """
    Delete category from database.
    
    Args:
        category_key: Category key to delete
    """
    await init_db_pool()
    
    sql = """
        DELETE FROM categories_config
        WHERE category_key = $1
    """
    
    await execute(sql, category_key)
    
    logger.info("category_deleted_from_database", category_key=category_key)


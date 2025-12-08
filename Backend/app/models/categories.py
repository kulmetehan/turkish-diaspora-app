# Backend/app/models/categories.py
"""
Central category registry - single source of truth for categories.

Loads category definitions from Infra/config/categories.yml and provides
a Category enum and metadata access functions.
"""

from __future__ import annotations

import yaml
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.core.logging import get_logger

# Path resolution
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent  # Backend/app
BACKEND_DIR = APP_DIR.parent  # Backend
REPO_ROOT = BACKEND_DIR.parent  # root
CATEGORIES_YML = REPO_ROOT / "Infra" / "config" / "categories.yml"


class Category(str, Enum):
    """Canonical category keys - single source of truth."""
    bakery = "bakery"
    restaurant = "restaurant"
    supermarket = "supermarket"
    barber = "barber"
    mosque = "mosque"
    travel_agency = "travel_agency"
    butcher = "butcher"
    fast_food = "fast_food"
    cafe = "cafe"
    car_dealer = "car_dealer"
    insurance = "insurance"
    tailor = "tailor"
    events_venue = "events_venue"
    community_centre = "community_centre"
    clinic = "clinic"
    other = "other"


class CategoryMetadata:
    """Metadata for a single category."""
    def __init__(
        self,
        key: str,
        label: str,
        description: str,
        aliases: List[str],
        google_types: List[str],
        osm_tags: Optional[Dict[str, Any]],
        discovery_enabled: bool,
        discovery_priority: int,
    ):
        self.key = key
        self.label = label
        self.description = description
        self.aliases = aliases
        self.google_types = google_types
        self.osm_tags = osm_tags
        self.discovery_enabled = discovery_enabled
        self.discovery_priority = discovery_priority

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "aliases": self.aliases,
            "google_types": self.google_types,
            "osm_tags": self.osm_tags,
            "is_discoverable": self.discovery_enabled,
            "discovery_priority": self.discovery_priority,
        }


# Cached category metadata
_CATEGORY_METADATA: Optional[Dict[str, CategoryMetadata]] = None


def _load_categories_config() -> Dict[str, Any]:
    """Load categories.yml file."""
    if not CATEGORIES_YML.exists():
        raise FileNotFoundError(f"Categories config not found: {CATEGORIES_YML}")
    
    with open(CATEGORIES_YML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError("categories.yml is invalid: missing 'categories' root key")
    
    return data.get("categories", {})


def _load_category_metadata() -> Dict[str, CategoryMetadata]:
    """Load and parse category metadata - database first, fallback to YAML."""
    global _CATEGORY_METADATA
    
    if _CATEGORY_METADATA is not None:
        return _CATEGORY_METADATA
    
    # Try database first
    try:
        from services.categories_db_service import load_categories_config_from_db
        import asyncio
        
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use run_until_complete
            # Fall through to YAML
            logger = get_logger()
            logger.debug("load_category_metadata_in_async_context_using_yaml_fallback")
        except RuntimeError:
            # No running loop, safe to create one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Try loading from database
            try:
                db_config = loop.run_until_complete(load_categories_config_from_db())
                categories = db_config.get("categories", {})
                
                # Only use database if it has categories
                if categories:
                    logger = get_logger()
                    logger.debug("load_category_metadata_loaded_from_database", category_count=len(categories))
                    metadata = _parse_from_db_config(categories)
                    _CATEGORY_METADATA = metadata
                    return metadata
                else:
                    logger = get_logger()
                    logger.warning("load_category_metadata_database_empty_falling_back_to_yaml")
            except Exception as e:
                logger = get_logger()
                logger.warning(
                    "load_category_metadata_database_load_failed",
                    error=str(e),
                    exc_info=e
                )
    except ImportError:
        # categories_db_service not available, fall through to YAML
        logger = get_logger()
        logger.debug("load_category_metadata_service_not_available_using_yaml")
    except Exception as e:
        logger = get_logger()
        logger.warning(
            "load_category_metadata_database_error_falling_back_to_yaml",
            error=str(e),
            exc_info=e
        )
    
    # Fallback to YAML
    categories_yaml = _load_categories_config()
    metadata = _parse_from_yaml(categories_yaml)
    
    logger = get_logger()
    logger.debug("load_category_metadata_loaded_from_yaml")
    _CATEGORY_METADATA = metadata
    return metadata


def _parse_from_db_config(categories: Dict[str, Any]) -> Dict[str, CategoryMetadata]:
    """Parse category metadata from database config structure."""
    metadata: Dict[str, CategoryMetadata] = {}
    
    for key, cat_def in categories.items():
        if not isinstance(cat_def, dict):
            continue
        
        discovery_cfg = cat_def.get("discovery", {})
        
        metadata[key] = CategoryMetadata(
            key=key,
            label=cat_def.get("label", key),
            description=cat_def.get("description", ""),
            aliases=cat_def.get("aliases", []),
            google_types=cat_def.get("google_types", []),
            osm_tags=cat_def.get("osm_tags"),
            discovery_enabled=discovery_cfg.get("enabled", True),
            discovery_priority=discovery_cfg.get("priority", 0),
        )
    
    return metadata


def _parse_from_yaml(categories_yaml: Dict[str, Any]) -> Dict[str, CategoryMetadata]:
    """Parse category metadata from YAML structure."""
    metadata: Dict[str, CategoryMetadata] = {}
    
    for key, cat_def in categories_yaml.items():
        if not isinstance(cat_def, dict):
            continue
        
        discovery_cfg = cat_def.get("discovery", {})
        
        metadata[key] = CategoryMetadata(
            key=key,
            label=cat_def.get("label", key),
            description=cat_def.get("description", ""),
            aliases=cat_def.get("aliases", []),
            google_types=cat_def.get("google_types", []),
            osm_tags=cat_def.get("osm_tags"),
            discovery_enabled=discovery_cfg.get("enabled", True),
            discovery_priority=discovery_cfg.get("priority", 0),
        )
    
    return metadata


def get_all_categories() -> List[CategoryMetadata]:
    """Get all category metadata, sorted by discovery priority (descending)."""
    metadata = _load_category_metadata()
    categories = list(metadata.values())
    # Sort by discovery priority (higher = more important), then by key
    categories.sort(key=lambda c: (-c.discovery_priority, c.key))
    return categories


def get_category_metadata(key: str) -> Optional[CategoryMetadata]:
    """Get metadata for a specific category key."""
    metadata = _load_category_metadata()
    return metadata.get(key)


def get_discoverable_categories() -> List[CategoryMetadata]:
    """Get only categories with discovery enabled."""
    return [c for c in get_all_categories() if c.discovery_enabled]


def clear_cache() -> None:
    """Clear cached metadata (useful for testing or hot-reload scenarios)."""
    global _CATEGORY_METADATA
    _CATEGORY_METADATA = None








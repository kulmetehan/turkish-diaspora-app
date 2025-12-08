"""
Cities Database Service - Manages cities and districts configuration in database.

This service provides database-driven access to cities configuration, replacing
the YAML-based approach to avoid synchronization issues between admin UI and
GitHub Actions.

All functions maintain backwards compatibility with the YAML structure format.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from services.db_service import fetch, fetchrow, execute, init_db_pool
from app.core.logging import get_logger
from app.workers.discovery_bot import CITIES_YML

logger = get_logger()


def _load_defaults_from_yaml() -> Dict[str, Any]:
    """Load defaults section from YAML file (still using YAML for defaults)."""
    try:
        if CITIES_YML.exists():
            import yaml
            data = yaml.safe_load(CITIES_YML.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("defaults", {})
    except Exception as e:
        logger.warning("failed_to_load_defaults_from_yaml", error=str(e))
    return {}


def _load_metadata_from_yaml() -> Dict[str, Any]:
    """Load metadata section from YAML file."""
    try:
        if CITIES_YML.exists():
            import yaml
            data = yaml.safe_load(CITIES_YML.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("metadata", {})
    except Exception as e:
        logger.warning("failed_to_load_metadata_from_yaml", error=str(e))
    return {}


async def load_cities_config_from_db() -> Dict[str, Any]:
    """
    Load all cities and districts from database.
    
    Returns same dict structure as YAML loader for backwards compatibility:
    {
        "version": 1,
        "metadata": {...},
        "defaults": {...},  # From YAML (still using YAML for defaults)
        "cities": {
            "city_key": {
                "city_name": "...",
                "country": "NL",
                "center_lat": ...,
                "center_lng": ...,
                "districts": {
                    "district_key": {
                        "lat_min": ...,
                        "lat_max": ...,
                        "lng_min": ...,
                        "lng_max": ...,
                        ...
                    }
                }
            }
        }
    }
    """
    await init_db_pool()
    
    try:
        # Load all cities
        cities_sql = """
            SELECT 
                city_key,
                city_name,
                country,
                center_lat,
                center_lng,
                config_json
            FROM cities_config
            ORDER BY city_key ASC
        """
        cities_rows = await fetch(cities_sql)
        
        if not cities_rows:
            logger.warning("no_cities_in_database")
            return {
                "version": 1,
                "metadata": _load_metadata_from_yaml(),
                "defaults": _load_defaults_from_yaml(),
                "cities": {}
            }
        
        # Load all districts
        districts_sql = """
            SELECT 
                city_key,
                district_key,
                lat_min,
                lat_max,
                lng_min,
                lng_max,
                config_json
            FROM districts_config
            ORDER BY city_key ASC, district_key ASC
        """
        districts_rows = await fetch(districts_sql)
        
        # Build cities dict
        cities_dict: Dict[str, Any] = {}
        
        for city_row in cities_rows:
            city_key = city_row["city_key"]
            config_json = city_row.get("config_json") or {}
            
            cities_dict[city_key] = {
                "city_name": city_row["city_name"],
                "country": city_row["country"],
                "center_lat": float(city_row["center_lat"]) if city_row["center_lat"] is not None else None,
                "center_lng": float(city_row["center_lng"]) if city_row["center_lng"] is not None else None,
                "districts": {}
            }
            
            # Add config_json fields if present (like "apply")
            if isinstance(config_json, dict):
                for key, value in config_json.items():
                    if key not in ["city_name", "country", "center_lat", "center_lng"]:
                        cities_dict[city_key][key] = value
        
        # Add districts to cities
        for district_row in districts_rows:
            city_key = district_row["city_key"]
            district_key = district_row["district_key"]
            config_json = district_row.get("config_json") or {}
            
            if city_key not in cities_dict:
                logger.warning("district_without_city", city_key=city_key, district_key=district_key)
                continue
            
            district_data: Dict[str, Any] = {
                "lat_min": float(district_row["lat_min"]),
                "lat_max": float(district_row["lat_max"]),
                "lng_min": float(district_row["lng_min"]),
                "lng_max": float(district_row["lng_max"]),
            }
            
            # Add config_json fields if present (like "apply")
            if isinstance(config_json, dict):
                for key, value in config_json.items():
                    if key not in ["lat_min", "lat_max", "lng_min", "lng_max"]:
                        district_data[key] = value
            
            cities_dict[city_key]["districts"][district_key] = district_data
        
        return {
            "version": 1,
            "metadata": _load_metadata_from_yaml(),
            "defaults": _load_defaults_from_yaml(),
            "cities": cities_dict
        }
        
    except Exception as e:
        logger.error("failed_to_load_cities_from_database", error=str(e), exc_info=e)
        raise


async def get_city_from_db(city_key: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific city from database.
    
    Returns city dict with same structure as YAML, or None if not found.
    """
    await init_db_pool()
    
    sql = """
        SELECT 
            city_key,
            city_name,
            country,
            center_lat,
            center_lng,
            config_json
        FROM cities_config
        WHERE city_key = $1
    """
    row = await fetchrow(sql, city_key)
    
    if not row:
        return None
    
    # Load districts for this city
    districts_sql = """
        SELECT 
            district_key,
            lat_min,
            lat_max,
            lng_min,
            lng_max,
            config_json
        FROM districts_config
        WHERE city_key = $1
        ORDER BY district_key ASC
    """
    districts_rows = await fetch(districts_sql, city_key)
    
    config_json = row.get("config_json") or {}
    city_data: Dict[str, Any] = {
        "city_name": row["city_name"],
        "country": row["country"],
        "center_lat": float(row["center_lat"]) if row["center_lat"] is not None else None,
        "center_lng": float(row["center_lng"]) if row["center_lng"] is not None else None,
        "districts": {}
    }
    
    # Add config_json fields if present
    if isinstance(config_json, dict):
        for key, value in config_json.items():
            if key not in ["city_name", "country", "center_lat", "center_lng"]:
                city_data[key] = value
    
    # Add districts
    for district_row in districts_rows:
        district_key = district_row["district_key"]
        district_config_json = district_row.get("config_json") or {}
        
        district_data: Dict[str, Any] = {
            "lat_min": float(district_row["lat_min"]),
            "lat_max": float(district_row["lat_max"]),
            "lng_min": float(district_row["lng_min"]),
            "lng_max": float(district_row["lng_max"]),
        }
        
        # Add config_json fields if present
        if isinstance(district_config_json, dict):
            for key, value in district_config_json.items():
                if key not in ["lat_min", "lat_max", "lng_min", "lng_max"]:
                    district_data[key] = value
        
        city_data["districts"][district_key] = district_data
    
    return city_data


async def get_districts_for_city(city_key: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all districts for a specific city.
    
    Returns dict mapping district_key to district data.
    """
    await init_db_pool()
    
    sql = """
        SELECT 
            district_key,
            lat_min,
            lat_max,
            lng_min,
            lng_max,
            config_json
        FROM districts_config
        WHERE city_key = $1
        ORDER BY district_key ASC
    """
    rows = await fetch(sql, city_key)
    
    districts: Dict[str, Dict[str, Any]] = {}
    
    for row in rows:
        district_key = row["district_key"]
        config_json = row.get("config_json") or {}
        
        district_data: Dict[str, Any] = {
            "lat_min": float(row["lat_min"]),
            "lat_max": float(row["lat_max"]),
            "lng_min": float(row["lng_min"]),
            "lng_max": float(row["lng_max"]),
        }
        
        # Add config_json fields if present
        if isinstance(config_json, dict):
            for key, value in config_json.items():
                if key not in ["lat_min", "lat_max", "lng_min", "lng_max"]:
                    district_data[key] = value
        
        districts[district_key] = district_data
    
    return districts


async def save_city_to_db(city_key: str, city_data: Dict[str, Any]) -> None:
    """
    Save city configuration to database (INSERT or UPDATE).
    
    Args:
        city_key: City key (normalized)
        city_data: City data dict with city_name, country, center_lat, center_lng, etc.
    """
    await init_db_pool()
    
    city_name = city_data.get("city_name")
    country = city_data.get("country", "NL")
    center_lat = city_data.get("center_lat")
    center_lng = city_data.get("center_lng")
    
    # Build config_json with extra fields (like "apply")
    config_json: Dict[str, Any] = {}
    for key, value in city_data.items():
        if key not in ["city_name", "country", "center_lat", "center_lng", "districts"]:
            config_json[key] = value
    
    sql = """
        INSERT INTO cities_config (
            city_key,
            city_name,
            country,
            center_lat,
            center_lng,
            config_json,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (city_key)
        DO UPDATE SET
            city_name = EXCLUDED.city_name,
            country = EXCLUDED.country,
            center_lat = EXCLUDED.center_lat,
            center_lng = EXCLUDED.center_lng,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    
    await execute(
        sql,
        city_key,
        city_name,
        country,
        center_lat,
        center_lng,
        json.dumps(config_json) if config_json else json.dumps({})
    )
    
    logger.info("city_saved_to_database", city_key=city_key, city_name=city_name)
    
    # Sync districts if provided
    districts = city_data.get("districts", {})
    if districts:
        for district_key, district_data in districts.items():
            await save_district_to_db(city_key, district_key, district_data)


async def save_district_to_db(city_key: str, district_key: str, district_data: Dict[str, Any]) -> None:
    """
    Save district configuration to database (INSERT or UPDATE).
    
    Args:
        city_key: City key
        district_key: District key (normalized)
        district_data: District data dict with lat_min, lat_max, lng_min, lng_max, etc.
    """
    await init_db_pool()
    
    lat_min = float(district_data["lat_min"])
    lat_max = float(district_data["lat_max"])
    lng_min = float(district_data["lng_min"])
    lng_max = float(district_data["lng_max"])
    
    # Build config_json with extra fields (like "apply")
    config_json: Dict[str, Any] = {}
    for key, value in district_data.items():
        if key not in ["lat_min", "lat_max", "lng_min", "lng_max"]:
            config_json[key] = value
    
    sql = """
        INSERT INTO districts_config (
            city_key,
            district_key,
            lat_min,
            lat_max,
            lng_min,
            lng_max,
            config_json,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (city_key, district_key)
        DO UPDATE SET
            lat_min = EXCLUDED.lat_min,
            lat_max = EXCLUDED.lat_max,
            lng_min = EXCLUDED.lng_min,
            lng_max = EXCLUDED.lng_max,
            config_json = EXCLUDED.config_json,
            updated_at = NOW()
    """
    
    await execute(
        sql,
        city_key,
        district_key,
        lat_min,
        lat_max,
        lng_min,
        lng_max,
        json.dumps(config_json) if config_json else json.dumps({})
    )
    
    logger.info("district_saved_to_database", city_key=city_key, district_key=district_key)


async def delete_city_from_db(city_key: str) -> None:
    """
    Delete city from database (CASCADE will automatically delete districts).
    
    Args:
        city_key: City key to delete
    """
    await init_db_pool()
    
    sql = """
        DELETE FROM cities_config
        WHERE city_key = $1
    """
    
    await execute(sql, city_key)
    
    logger.info("city_deleted_from_database", city_key=city_key)


async def delete_district_from_db(city_key: str, district_key: str) -> None:
    """
    Delete district from database.
    
    Args:
        city_key: City key
        district_key: District key to delete
    """
    await init_db_pool()
    
    sql = """
        DELETE FROM districts_config
        WHERE city_key = $1 AND district_key = $2
    """
    
    await execute(sql, city_key, district_key)
    
    logger.info("district_deleted_from_database", city_key=city_key, district_key=district_key)


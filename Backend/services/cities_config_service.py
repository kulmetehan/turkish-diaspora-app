"""
Service for managing cities.yml configuration file.

Provides functions for reading, writing, and validating city/district configurations.
Handles YAML file operations with automatic backups and validation.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.logging import get_logger
from app.workers.discovery_bot import CITIES_YML, DEFAULT_DISTRICT_LAT_DELTA, DEFAULT_DISTRICT_LNG_DELTA

logger = get_logger()

# Maximum number of backups to keep
MAX_BACKUPS = 5


def calculate_district_bbox(
    center_lat: float,
    center_lng: float,
    lat_delta: float = DEFAULT_DISTRICT_LAT_DELTA,
    lng_delta: float = DEFAULT_DISTRICT_LNG_DELTA,
) -> Dict[str, float]:
    """
    Calculate bounding box for a district from center coordinates.
    
    Args:
        center_lat: Center latitude
        center_lng: Center longitude
        lat_delta: Latitude delta (default from discovery_bot)
        lng_delta: Longitude delta (default from discovery_bot)
    
    Returns:
        Dictionary with lat_min, lat_max, lng_min, lng_max
    """
    return {
        "lat_min": center_lat - lat_delta,
        "lat_max": center_lat + lat_delta,
        "lng_min": center_lng - lng_delta,
        "lng_max": center_lng + lng_delta,
    }


def calculate_center_from_bbox(bbox: Dict[str, float]) -> tuple[float, float]:
    """
    Calculate center coordinates from a bounding box.
    
    Args:
        bbox: Dictionary with lat_min, lat_max, lng_min, lng_max
    
    Returns:
        Tuple of (center_lat, center_lng)
    """
    center_lat = (bbox["lat_min"] + bbox["lat_max"]) / 2.0
    center_lng = (bbox["lng_min"] + bbox["lng_max"]) / 2.0
    return center_lat, center_lng


def validate_coordinates(lat: float, lng: float, name: str = "coordinates") -> None:
    """Validate latitude and longitude are within valid ranges."""
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"{name}: latitude must be between -90 and 90, got {lat}")
    if not (-180.0 <= lng <= 180.0):
        raise ValueError(f"{name}: longitude must be between -180 and 180, got {lng}")


def validate_district_bbox(bbox: Dict[str, float]) -> None:
    """Validate bounding box coordinates."""
    required_keys = {"lat_min", "lat_max", "lng_min", "lng_max"}
    missing = required_keys - set(bbox.keys())
    if missing:
        raise ValueError(f"Bounding box missing required keys: {missing}")
    
    lat_min = float(bbox["lat_min"])
    lat_max = float(bbox["lat_max"])
    lng_min = float(bbox["lng_min"])
    lng_max = float(bbox["lng_max"])
    
    if not (-90.0 <= lat_min < lat_max <= 90.0):
        raise ValueError(f"Invalid latitude range: {lat_min}..{lat_max}")
    if not (-180.0 <= lng_min < lng_max <= 180.0):
        raise ValueError(f"Invalid longitude range: {lng_min}..{lng_max}")


def validate_city_key(city_key: str) -> None:
    """Validate city key format (lowercase with underscores)."""
    if not city_key:
        raise ValueError("City key cannot be empty")
    if not city_key.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"City key must be alphanumeric with underscores/dashes: {city_key}")
    if not city_key.islower():
        raise ValueError(f"City key must be lowercase: {city_key}")


def validate_district_key(district_key: str) -> None:
    """Validate district key format (lowercase with underscores)."""
    if not district_key:
        raise ValueError("District key cannot be empty")
    if not district_key.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"District key must be alphanumeric with underscores/dashes: {district_key}")
    if not district_key.islower():
        raise ValueError(f"District key must be lowercase: {district_key}")


def validate_city_config(city_key: str, city_data: Dict[str, Any]) -> None:
    """Validate city configuration structure."""
    validate_city_key(city_key)
    
    if not isinstance(city_data, dict):
        raise ValueError("City data must be a dictionary")
    
    city_name = city_data.get("city_name")
    if not city_name or not isinstance(city_name, str) or not city_name.strip():
        raise ValueError("city_name is required and must be a non-empty string")
    
    country = city_data.get("country", "NL")
    if not isinstance(country, str) or len(country) != 2:
        raise ValueError("country must be a 2-letter code (default: NL)")
    
    # Validate center coordinates if present
    center_lat = city_data.get("center_lat")
    center_lng = city_data.get("center_lng")
    if center_lat is not None:
        validate_coordinates(float(center_lat), float(center_lng or 0), "city center")
    
    # Validate districts if present
    districts = city_data.get("districts", {})
    if districts and not isinstance(districts, dict):
        raise ValueError("districts must be a dictionary")
    
    for district_key, district_data in districts.items():
        validate_district_key(district_key)
        if not isinstance(district_data, dict):
            raise ValueError(f"District {district_key} data must be a dictionary")
        
        # Validate district bbox if present
        bbox_keys = {"lat_min", "lat_max", "lng_min", "lng_max"}
        if bbox_keys.issubset(district_data.keys()):
            validate_district_bbox(district_data)


def normalize_city_key(name: str) -> str:
    """Convert city name to valid key format (lowercase, underscores for spaces)."""
    # Convert to lowercase, replace spaces and special chars with underscores
    key = name.lower().strip()
    # Replace spaces and special characters with underscores
    key = "".join(c if c.isalnum() else "_" for c in key)
    # Remove consecutive underscores
    while "__" in key:
        key = key.replace("__", "_")
    # Remove leading/trailing underscores
    key = key.strip("_")
    return key


def normalize_district_key(name: str) -> str:
    """Convert district name to valid key format (lowercase, underscores for spaces)."""
    return normalize_city_key(name)  # Same logic


def create_backup(file_path: Path) -> Path:
    """Create a timestamped backup of the cities.yml file."""
    if not file_path.exists():
        logger.warning("cities_yml_not_found_for_backup", path=str(file_path))
        return file_path
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.name}.backup.{timestamp}"
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info("cities_yml_backup_created", backup_path=str(backup_path))
        return backup_path
    except Exception as e:
        logger.error("cities_yml_backup_failed", error=str(e), exc_info=e)
        raise


def cleanup_old_backups(file_path: Path) -> None:
    """Remove old backup files, keeping only the most recent MAX_BACKUPS."""
    backup_pattern = f"{file_path.name}.backup.*"
    backups = sorted(file_path.parent.glob(backup_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if len(backups) > MAX_BACKUPS:
        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink()
                logger.info("old_backup_removed", path=str(old_backup))
            except Exception as e:
                logger.warning("old_backup_removal_failed", path=str(old_backup), error=str(e))


def load_cities_config() -> Dict[str, Any]:
    """
    Load cities configuration - database first, fallback to YAML.
    
    This is a wrapper around discovery_bot.load_cities_config() which
    implements database-first loading with YAML fallback.
    """
    from app.workers.discovery_bot import load_cities_config as _load
    
    return _load()


def get_city_key_from_coords(lat: Optional[float], lng: Optional[float]) -> Optional[str]:
    """
    Derive city_key from coordinates by checking which city's bbox contains the point.
    
    Args:
        lat: Latitude
        lng: Longitude
    
    Returns:
        city_key (e.g., 'rotterdam') if coordinates fall within a city's districts, None otherwise
    """
    if lat is None or lng is None:
        return None
    
    try:
        config = load_cities_config()
        cities = config.get("cities", {})
        
        # Check each city's districts
        for city_key, city_data in cities.items():
            districts = city_data.get("districts", {})
            
            # Check if point is within any district's bbox
            for district_key, district_data in districts.items():
                if all(k in district_data for k in ["lat_min", "lat_max", "lng_min", "lng_max"]):
                    lat_min = float(district_data["lat_min"])
                    lat_max = float(district_data["lat_max"])
                    lng_min = float(district_data["lng_min"])
                    lng_max = float(district_data["lng_max"])
                    
                    if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
                        return city_key
        
        # If no district match, check city-level bbox if it exists
        for city_key, city_data in cities.items():
            if all(k in city_data for k in ["lat_min", "lat_max", "lng_min", "lng_max"]):
                lat_min = float(city_data["lat_min"])
                lat_max = float(city_data["lat_max"])
                lng_min = float(city_data["lng_min"])
                lng_max = float(city_data["lng_max"])
                
                if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
                    return city_key
        
        return None
    except Exception as e:
        logger.warning("failed_to_get_city_key_from_coords", lat=lat, lng=lng, error=str(e))
        return None


def get_defaults_anchor_ref(config: Dict[str, Any]) -> str:
    """
    Get the YAML anchor reference for defaults section.
    
    Tries to find the anchor name by:
    1. Checking existing cities for their 'apply' value
    2. Reading raw YAML to find anchor name
    3. Falling back to '*id001' if no reference found
    
    Args:
        config: Cities configuration dictionary
    
    Returns:
        Anchor reference string (e.g., '*id001')
    """
    # First, try to find anchor from existing cities
    cities = config.get("cities", {})
    for city_data in cities.values():
        if isinstance(city_data, dict) and "apply" in city_data:
            apply_value = city_data["apply"]
            if isinstance(apply_value, str) and apply_value.startswith("*"):
                return apply_value
    
    # Fallback: try to read raw YAML to find anchor name
    try:
        from app.workers.discovery_bot import CITIES_YML
        raw_yaml = CITIES_YML.read_text(encoding="utf-8")
        # Look for pattern: defaults: &anchor_name
        import re
        match = re.search(r'defaults:\s*&(\w+)', raw_yaml)
        if match:
            return f"*{match.group(1)}"
    except Exception:
        pass
    
    # Final fallback
    return "*id001"


def save_cities_config(config: Dict[str, Any]) -> None:
    """
    Save cities configuration to YAML file with backup.
    
    Args:
        config: Complete cities configuration dictionary
    
    Raises:
        ValueError: If configuration is invalid
        IOError: If file write fails
    """
    # Validate structure
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")
    
    if "cities" not in config:
        raise ValueError("Configuration must contain 'cities' key")
    
    # Create backup before writing
    backup_path = create_backup(CITIES_YML)
    
    try:
        # Validate all cities in config
        cities = config.get("cities", {})
        for city_key, city_data in cities.items():
            validate_city_config(city_key, city_data)
        
        # Sort cities alphabetically for consistent output
        sorted_cities = dict(sorted(cities.items()))
        
        # Sort districts within each city
        for city_key in sorted_cities:
            districts = sorted_cities[city_key].get("districts", {})
            if districts:
                sorted_cities[city_key]["districts"] = dict(sorted(districts.items()))
        
        # Create new config with sorted cities
        sorted_config = {**config, "cities": sorted_cities}
        
        # Write YAML with proper formatting
        yaml_content = yaml.dump(
            sorted_config,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,  # Preserve order (version, metadata, defaults, cities)
            width=120,
            indent=2,
        )
        
        # Post-process to restore YAML anchor references
        # Replace string representation of anchor references with actual anchor syntax
        # Find all anchor references in the config and ensure they're not quoted
        import re
        # Match any anchor reference pattern like "*id001" or "*rotterdam_defaults"
        yaml_content = re.sub(r'"(\*\w+)"', r'\1', yaml_content)
        yaml_content = re.sub(r"'(\*\w+)'", r'\1', yaml_content)
        
        # Ensure file directory exists
        CITIES_YML.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        CITIES_YML.write_text(yaml_content, encoding="utf-8")
        
        logger.info("cities_yml_saved", path=str(CITIES_YML))
        
        # Cleanup old backups
        cleanup_old_backups(CITIES_YML)
        
    except Exception as e:
        # Restore from backup if write failed
        logger.error("cities_yml_save_failed", error=str(e), exc_info=e)
        if backup_path.exists() and backup_path != CITIES_YML:
            try:
                shutil.copy2(backup_path, CITIES_YML)
                logger.info("cities_yml_restored_from_backup", backup_path=str(backup_path))
            except Exception as restore_error:
                logger.error("cities_yml_restore_failed", error=str(restore_error))
        raise


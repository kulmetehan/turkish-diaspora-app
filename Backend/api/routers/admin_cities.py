from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.metrics import CitiesOverview, CityReadiness
from app.core.logging import get_logger
from app.workers.discovery_bot import load_cities_config
from services.metrics_service import _city_progress, _compute_city_bbox

logger = get_logger()

router = APIRouter(
    prefix="/admin/cities",
    tags=["admin-cities"],
)


def _determine_readiness_status(
    city_key: str,
    has_districts: bool,
    districts_count: int,
    verified_count: int,
    candidate_count: int,
) -> tuple[str, str]:
    """
    Determine readiness status and notes for a city.
    
    Returns (status, notes) tuple.
    """
    if not has_districts or districts_count == 0:
        return (
            "config_incomplete",
            "No districts defined in cities.yml. Add district bounding boxes to enable discovery.",
        )
    
    total_locations = verified_count + candidate_count
    if total_locations == 0:
        return (
            "configured_inactive",
            "City is configured but has no locations yet. Run discovery bot to start finding locations.",
        )
    
    # Rotterdam is considered "active" if it has data
    if city_key == "rotterdam":
        return (
            "active",
            "City is active with discovery and verification running.",
        )
    
    # Other cities with data are "configured_inactive" until we mark them as active
    if total_locations > 0:
        return (
            "configured_inactive",
            "City has locations but is not yet marked as active. Consider promoting to active status.",
        )
    
    return (
        "configured_inactive",
        "City is configured but inactive.",
    )


@router.get("", response_model=CitiesOverview)
async def get_cities_overview(
    admin: AdminUser = Depends(verify_admin_user),
) -> CitiesOverview:
    """
    Get overview of all cities with their configuration and readiness status.
    
    Returns metrics for each city defined in cities.yml, including:
    - Configuration status (districts defined)
    - Location counts (verified, candidates)
    - Readiness status (active, configured_inactive, config_incomplete)
    """
    try:
        cfg = load_cities_config()
        cities_def = cfg.get("cities", {})
        
        if not cities_def:
            logger.warning("no_cities_in_config")
            return CitiesOverview(cities=[])
        
        city_readiness_list: List[CityReadiness] = []
        
        for city_key, city_data in cities_def.items():
            if not isinstance(city_data, dict):
                logger.warning("invalid_city_data", city_key=city_key)
                continue
            
            city_name = city_data.get("city_name", city_key.title())
            districts = city_data.get("districts", {})
            has_districts = bool(districts) and isinstance(districts, dict)
            districts_count = len(districts) if has_districts else 0
            
            # Compute metrics if we have districts
            verified_count = 0
            candidate_count = 0
            coverage_ratio = 0.0
            growth_weekly: float | None = None
            
            if has_districts:
                progress = await _city_progress(city_key)
                if progress:
                    verified_count = progress.verified_count
                    candidate_count = progress.candidate_count
                    coverage_ratio = progress.coverage_ratio
                    growth_weekly = progress.growth_weekly
            
            # Determine readiness status
            readiness_status, readiness_notes = _determine_readiness_status(
                city_key=city_key,
                has_districts=has_districts,
                districts_count=districts_count,
                verified_count=verified_count,
                candidate_count=candidate_count,
            )
            
            city_readiness = CityReadiness(
                city_key=city_key,
                city_name=city_name,
                has_districts=has_districts,
                districts_count=districts_count,
                verified_count=verified_count,
                candidate_count=candidate_count,
                coverage_ratio=coverage_ratio,
                growth_weekly=growth_weekly,
                readiness_status=readiness_status,
                readiness_notes=readiness_notes,
            )
            
            city_readiness_list.append(city_readiness)
        
        return CitiesOverview(cities=city_readiness_list)
    
    except FileNotFoundError:
        logger.error("cities_yml_not_found")
        raise HTTPException(
            status_code=500,
            detail="cities.yml configuration file not found",
        )
    except Exception as e:
        logger.exception("failed_to_load_cities_overview", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load cities overview: {str(e)}",
        )


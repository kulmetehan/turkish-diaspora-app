from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_cities import (
    CityCreate,
    CityUpdate,
    DistrictCreate,
    DistrictUpdate,
    CityDetailResponse,
    DistrictDetail,
)
from app.models.metrics import CitiesOverview, CityReadiness
from app.core.logging import get_logger
from app.workers.discovery_bot import load_cities_config
from services.metrics_service import _city_progress, _compute_city_bbox
from services.cities_config_service import (
    calculate_center_from_bbox,
    calculate_district_bbox,
    load_cities_config as load_config,
    normalize_city_key,
    normalize_district_key,
    validate_city_config,
    get_defaults_anchor_ref,
)
from services.cities_db_service import (
    load_cities_config_from_db,
    get_city_from_db,
    save_city_to_db,
    save_district_to_db,
    delete_city_from_db,
    delete_district_from_db,
)

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
        # Load from database first
        try:
            cfg = await load_cities_config_from_db()
        except Exception as e:
            logger.warning("failed_to_load_cities_from_db_falling_back_to_yaml", error=str(e))
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
                try:
                    progress = await _city_progress(city_key)
                    if progress:
                        verified_count = progress.verified_count
                        candidate_count = progress.candidate_count
                        coverage_ratio = progress.coverage_ratio
                        growth_weekly = progress.growth_weekly
                except Exception as e:
                    # Log error but continue processing other cities
                    logger.warning(
                        "failed_to_compute_city_progress",
                        city_key=city_key,
                        error=str(e),
                        exc_info=e
                    )
                    # Keep default values (0 counts, 0.0 coverage)
            
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


@router.get("/{city_key}", response_model=CityDetailResponse)
async def get_city_detail(
    city_key: str = Path(..., description="City key from cities.yml"),
    admin: AdminUser = Depends(verify_admin_user),
) -> CityDetailResponse:
    """
    Get full details for a specific city including all districts with their coordinates.
    
    Returns complete city configuration with:
    - City name, country, center coordinates
    - List of all districts with keys, names, center coordinates, and bounding boxes
    """
    try:
        # Load from database first
        try:
            city_data = await get_city_from_db(city_key)
            if not city_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"City '{city_key}' not found",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("failed_to_load_city_from_db_falling_back_to_yaml", city_key=city_key, error=str(e))
            # Fallback to YAML for backwards compatibility
            config = load_config()
            cities = config.get("cities", {})
            if city_key not in cities:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"City '{city_key}' not found",
                )
            city_data = cities[city_key]
        
        # Extract city info
        city_name = city_data.get("city_name", city_key.title())
        country = city_data.get("country", "NL")
        center_lat = city_data.get("center_lat", 0.0)
        center_lng = city_data.get("center_lng", 0.0)
        
        # Process districts
        districts_list: List[DistrictDetail] = []
        districts_data = city_data.get("districts", {})
        
        for district_key, district_data in districts_data.items():
            if not isinstance(district_data, dict):
                continue
            
            # Get bounding box
            bbox = {
                "lat_min": float(district_data.get("lat_min", 0.0)),
                "lat_max": float(district_data.get("lat_max", 0.0)),
                "lng_min": float(district_data.get("lng_min", 0.0)),
                "lng_max": float(district_data.get("lng_max", 0.0)),
            }
            
            # Calculate center from bbox if not explicitly provided
            if "center_lat" in district_data and "center_lng" in district_data:
                district_center_lat = float(district_data["center_lat"])
                district_center_lng = float(district_data["center_lng"])
            else:
                district_center_lat, district_center_lng = calculate_center_from_bbox(bbox)
            
            # District name: try to derive from key (capitalize words)
            district_name = district_key.replace("_", " ").replace("-", " ").title()
            
            districts_list.append(DistrictDetail(
                key=district_key,
                name=district_name,
                center_lat=district_center_lat,
                center_lng=district_center_lng,
                bbox=bbox,
            ))
        
        # Sort districts alphabetically by key
        districts_list.sort(key=lambda d: d.key)
        
        return CityDetailResponse(
            city_key=city_key,
            city_name=city_name,
            country=country,
            center_lat=float(center_lat),
            center_lng=float(center_lng),
            districts=districts_list,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("failed_to_load_city_detail", city_key=city_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load city details: {str(e)}",
        ) from e


async def _get_city_readiness(city_key: str, city_data: Optional[Dict[str, Any]] = None) -> CityReadiness:
    """Helper to create CityReadiness from city config and metrics."""
    if city_data is None:
        city_data = await get_city_from_db(city_key) or {}
    city_name = city_data.get("city_name", city_key.title())
    districts = city_data.get("districts", {})
    has_districts = bool(districts) and isinstance(districts, dict)
    districts_count = len(districts) if has_districts else 0
    
    verified_count = 0
    candidate_count = 0
    coverage_ratio = 0.0
    growth_weekly: float | None = None
    
    if has_districts:
        try:
            progress = await _city_progress(city_key)
            if progress:
                verified_count = progress.verified_count
                candidate_count = progress.candidate_count
                coverage_ratio = progress.coverage_ratio
                growth_weekly = progress.growth_weekly
        except Exception as e:
            logger.warning(
                "failed_to_compute_city_progress",
                city_key=city_key,
                error=str(e),
                exc_info=e
            )
    
    readiness_status, readiness_notes = _determine_readiness_status(
        city_key=city_key,
        has_districts=has_districts,
        districts_count=districts_count,
        verified_count=verified_count,
        candidate_count=candidate_count,
    )
    
    return CityReadiness(
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


@router.post("", response_model=CityReadiness, status_code=status.HTTP_201_CREATED)
async def create_city(
    payload: CityCreate,
    admin: AdminUser = Depends(verify_admin_user),
) -> CityReadiness:
    """
    Create a new city with optional districts.
    
    The city key is automatically generated from the city name (lowercase, underscores).
    """
    try:
        # Generate city key from name
        city_key = normalize_city_key(payload.city_name)
        
        # Check if city already exists in database
        existing_city = await get_city_from_db(city_key)
        if existing_city:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"City with key '{city_key}' already exists",
            )
        
        # Get the defaults anchor reference dynamically (from YAML)
        try:
            config = await load_cities_config_from_db()
        except Exception:
            config = load_config()
        anchor_ref = get_defaults_anchor_ref(config)
        
        # Build city data structure
        city_data: Dict[str, Any] = {
            "city_name": payload.city_name,
            "country": payload.country,
            "center_lat": payload.center_lat,
            "center_lng": payload.center_lng,
            "apply": anchor_ref,  # Use dynamic anchor reference
        }
        
        # Add districts if provided
        if payload.districts:
            districts_dict: Dict[str, Any] = {}
            for district in payload.districts:
                district_key = normalize_district_key(district.name)
                if district_key in districts_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate district name: {district.name}",
                    )
                
                bbox = calculate_district_bbox(district.center_lat, district.center_lng)
                districts_dict[district_key] = {
                    **bbox,
                    "apply": anchor_ref,  # Use dynamic anchor reference
                }
            city_data["districts"] = districts_dict
        
        # Validate city config
        validate_city_config(city_key, city_data)
        
        # Save to database
        await save_city_to_db(city_key, city_data)
        
        logger.info(
            "city_created",
            city_key=city_key,
            city_name=payload.city_name,
            districts_count=len(city_data.get("districts", {})),
            admin=admin.email,
        )
        
        # Load city data for readiness (already saved to DB)
        city_data_for_readiness = await get_city_from_db(city_key) or city_data
        # Return city readiness
        return await _get_city_readiness(city_key, city_data_for_readiness)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("failed_to_create_city", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create city: {str(e)}",
        ) from e


@router.put("/{city_key}", response_model=CityReadiness)
async def update_city(
    city_key: str,
    payload: CityUpdate,
    admin: AdminUser = Depends(verify_admin_user),
) -> CityReadiness:
    """Update an existing city's properties."""
    try:
        # Load existing city from database
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Update fields if provided
        if payload.city_name is not None:
            city_data["city_name"] = payload.city_name
        if payload.country is not None:
            city_data["country"] = payload.country
        if payload.center_lat is not None:
            city_data["center_lat"] = payload.center_lat
        if payload.center_lng is not None:
            city_data["center_lng"] = payload.center_lng
        
        # Validate updated config
        validate_city_config(city_key, city_data)
        
        # Save to database
        await save_city_to_db(city_key, city_data)
        
        logger.info(
            "city_updated",
            city_key=city_key,
            admin=admin.email,
        )
        
        # Load updated city data for readiness
        updated_city_data = await get_city_from_db(city_key) or city_data
        return await _get_city_readiness(city_key, updated_city_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("failed_to_update_city", city_key=city_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update city: {str(e)}",
        ) from e


@router.delete("/{city_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city(
    city_key: str,
    admin: AdminUser = Depends(verify_admin_user),
) -> None:
    """Delete a city and all its districts."""
    try:
        # Check if city exists
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Delete from database (CASCADE will remove districts)
        await delete_city_from_db(city_key)
        
        logger.info(
            "city_deleted",
            city_key=city_key,
            admin=admin.email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("failed_to_delete_city", city_key=city_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete city: {str(e)}",
        ) from e


@router.post("/{city_key}/districts", status_code=status.HTTP_201_CREATED)
async def create_district(
    city_key: str,
    payload: DistrictCreate,
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """Add a new district to an existing city."""
    try:
        # Check if city exists
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Check if district already exists
        districts = city_data.get("districts", {})
        district_key = normalize_district_key(payload.name)
        
        if district_key in districts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"District '{district_key}' already exists in city '{city_key}'",
            )
        
        # Get the defaults anchor reference dynamically (from YAML)
        try:
            config = await load_cities_config_from_db()
        except Exception:
            config = load_config()
        anchor_ref = get_defaults_anchor_ref(config)
        
        # Calculate bounding box
        bbox = calculate_district_bbox(payload.center_lat, payload.center_lng)
        district_data = {
            **bbox,
            "apply": anchor_ref,  # Use dynamic anchor reference
        }
        
        # Save district to database
        await save_district_to_db(city_key, district_key, district_data)
        
        logger.info(
            "district_created",
            city_key=city_key,
            district_key=district_key,
            admin=admin.email,
        )
        
        return {
            "ok": True,
            "city_key": city_key,
            "district_key": district_key,
            "bbox": bbox,
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("failed_to_create_district", city_key=city_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create district: {str(e)}",
        ) from e


@router.put("/{city_key}/districts/{district_key}", status_code=status.HTTP_200_OK)
async def update_district(
    city_key: str = Path(..., description="City key"),
    district_key: str = Path(..., description="District key"),
    payload: DistrictUpdate = ...,
    admin: AdminUser = Depends(verify_admin_user),
) -> Dict[str, Any]:
    """Update an existing district."""
    try:
        # Check if city exists
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Check if district exists
        districts = city_data.get("districts", {})
        if district_key not in districts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"District '{district_key}' not found in city '{city_key}'",
            )
        
        district_data = districts[district_key].copy()
        
        # Determine new center coordinates
        center_lat = payload.center_lat if payload.center_lat is not None else district_data.get("lat_min", 0) + (district_data.get("lat_max", 0) - district_data.get("lat_min", 0)) / 2
        center_lng = payload.center_lng if payload.center_lng is not None else district_data.get("lng_min", 0) + (district_data.get("lng_max", 0) - district_data.get("lng_min", 0)) / 2
        
        # If center changed, recalculate bbox
        if payload.center_lat is not None or payload.center_lng is not None:
            bbox = calculate_district_bbox(center_lat, center_lng)
            district_data.update(bbox)
        
        # If name changed, we need to rename the key (delete old, create new)
        final_district_key = district_key
        if payload.name and payload.name.strip():
            new_key = normalize_district_key(payload.name)
            if new_key != district_key:
                # Check if new key already exists
                city_check = await get_city_from_db(city_key)
                if city_check and new_key in city_check.get("districts", {}):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"District key '{new_key}' already exists",
                    )
                # Delete old district
                await delete_district_from_db(city_key, district_key)
                final_district_key = new_key
        
        # Save updated district to database
        await save_district_to_db(city_key, final_district_key, district_data)
        
        logger.info(
            "district_updated",
            city_key=city_key,
            district_key=final_district_key,
            admin=admin.email,
        )
        
        return {
            "ok": True,
            "city_key": city_key,
            "district_key": final_district_key,
            "bbox": {
                "lat_min": district_data["lat_min"],
                "lat_max": district_data["lat_max"],
                "lng_min": district_data["lng_min"],
                "lng_max": district_data["lng_max"],
            },
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("failed_to_update_district", city_key=city_key, district_key=district_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update district: {str(e)}",
        ) from e


@router.get("/{city_key}/districts/{district_key}", response_model=DistrictDetail)
async def get_district_detail(
    city_key: str = Path(..., description="City key"),
    district_key: str = Path(..., description="District key"),
    admin: AdminUser = Depends(verify_admin_user),
) -> DistrictDetail:
    """
    Get details for a specific district.
    
    Returns district configuration with key, name, center coordinates, and bounding box.
    """
    try:
        # Check if city exists
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Check if district exists
        districts = city_data.get("districts", {})
        if district_key not in districts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"District '{district_key}' not found in city '{city_key}'",
            )
        
        district_data = districts[district_key]
        
        # Get bounding box
        bbox = {
            "lat_min": float(district_data.get("lat_min", 0.0)),
            "lat_max": float(district_data.get("lat_max", 0.0)),
            "lng_min": float(district_data.get("lng_min", 0.0)),
            "lng_max": float(district_data.get("lng_max", 0.0)),
        }
        
        # Calculate center from bbox if not explicitly provided
        if "center_lat" in district_data and "center_lng" in district_data:
            district_center_lat = float(district_data["center_lat"])
            district_center_lng = float(district_data["center_lng"])
        else:
            district_center_lat, district_center_lng = calculate_center_from_bbox(bbox)
        
        # District name: try to derive from key (capitalize words)
        district_name = district_key.replace("_", " ").replace("-", " ").title()
        
        return DistrictDetail(
            key=district_key,
            name=district_name,
            center_lat=district_center_lat,
            center_lng=district_center_lng,
            bbox=bbox,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("failed_to_load_district_detail", city_key=city_key, district_key=district_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load district details: {str(e)}",
        ) from e


@router.delete("/{city_key}/districts/{district_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_district(
    city_key: str = Path(..., description="City key"),
    district_key: str = Path(..., description="District key"),
    admin: AdminUser = Depends(verify_admin_user),
) -> None:
    """Delete a district from a city."""
    try:
        # Check if city exists
        city_data = await get_city_from_db(city_key)
        if not city_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City '{city_key}' not found",
            )
        
        # Check if district exists
        districts = city_data.get("districts", {})
        if district_key not in districts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"District '{district_key}' not found in city '{city_key}'",
            )
        
        # Delete district from database
        await delete_district_from_db(city_key, district_key)
        
        logger.info(
            "district_deleted",
            city_key=city_key,
            district_key=district_key,
            admin=admin.email,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("failed_to_delete_district", city_key=city_key, district_key=district_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete district: {str(e)}",
        ) from e


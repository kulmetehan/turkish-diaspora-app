"""
Shared location filter definitions.

This module provides the single source of truth for verified location filters
used by both Admin metrics and the public locations API. Both endpoints must
remain in sync with the filters defined here.

The verified filter includes:
- state = 'VERIFIED'
- confidence_score >= 0.80
- is_retired = false OR is_retired IS NULL
- lat IS NOT NULL AND lng IS NOT NULL
- Optional bounding box filter for geographic scoping
"""

from typing import Optional, Tuple


# Confidence threshold for verified locations (matches frontend map)
VERIFIED_CONFIDENCE_THRESHOLD = 0.80


def get_verified_filter_sql(
    bbox: Optional[Tuple[float, float, float, float]] = None,
    alias: str = "",
) -> Tuple[str, list]:
    """
    Generate SQL WHERE clause for verified locations with standard filters.

    This is the canonical filter definition used by:
    - Admin metrics (_rotterdam_progress)
    - Public locations API (list_locations)

    Both endpoints must use this function to maintain parity.

    Args:
        bbox: Optional (lat_min, lat_max, lng_min, lng_max) bounding box.
              If provided, adds bbox filter to WHERE clause.
        alias: Optional table alias prefix (e.g., "l." for "l.state").

    Returns:
        Tuple of (sql_where_clause, parameters_list)
        The WHERE clause includes the base verified filters and optionally bbox.
        Parameters are bound values for the SQL query in order for asyncpg $1, $2, etc.

    Example:
        >>> sql, params = get_verified_filter_sql()
        >>> # sql = "state = 'VERIFIED' AND ..."
        >>> sql, params = get_verified_filter_sql(bbox=(51.85, 51.98, 4.35, 4.55))
        >>> # sql includes bbox filter
    """
    prefix = f"{alias}." if alias else ""
    conditions = []
    params = []
    param_num = 1

    # Base verified filters (single source of truth)
    conditions.append(f"{prefix}state = 'VERIFIED'")
    conditions.append(
        f"({prefix}confidence_score IS NOT NULL AND {prefix}confidence_score >= ${param_num})"
    )
    params.append(VERIFIED_CONFIDENCE_THRESHOLD)
    param_num += 1

    conditions.append(
        f"({prefix}is_retired = false OR {prefix}is_retired IS NULL)"
    )
    conditions.append(f"{prefix}lat IS NOT NULL")
    conditions.append(f"{prefix}lng IS NOT NULL")

    # Optional bbox filter
    if bbox:
        lat_min, lat_max, lng_min, lng_max = bbox
        conditions.append(f"{prefix}lat BETWEEN ${param_num} AND ${param_num + 1}")
        conditions.append(f"{prefix}lng BETWEEN ${param_num + 2} AND ${param_num + 3}")
        params.extend([float(lat_min), float(lat_max), float(lng_min), float(lng_max)])
        param_num += 4

    sql = " AND ".join(conditions)
    return sql, params


def get_verified_filter_params() -> dict:
    """
    Return filter parameters as a dictionary for UI display.

    Returns:
        Dictionary with filter criteria for transparency in Admin UI.
    """
    return {
        "state": "VERIFIED",
        "confidence_threshold": VERIFIED_CONFIDENCE_THRESHOLD,
        "exclude_retired": True,
        "require_coordinates": True,
    }


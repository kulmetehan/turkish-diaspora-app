# Backend/services/role_service.py
"""
Role Service

Calculates and assigns user roles based on activity patterns.
Roles are assigned based on:
- Check-ins: frequency and consistency
- Söz (location_notes): quantity and quality (reactions)
- Poll responses: quantity and consistency
- Activity summary: aggregated metrics
"""
from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID
import logging

from services.db_service import fetch, fetchrow, execute

logger = logging.getLogger(__name__)

# Role type constants (matching ENUM values)
ROLE_YENI_GELEN = "yeni_gelen"
ROLE_MAHALLELI = "mahalleli"
ROLE_ANLATICI = "anlatıcı"
ROLE_SES_VEREN = "ses_veren"
ROLE_SOZU_DINLENIR = "sözü_dinlenir"
ROLE_YERINDE_TESPIT = "yerinde_tespit"
ROLE_SESSIZ_GUC = "sessiz_güç"


async def assign_role(
    user_id: UUID,
    role: str,
    city_key: Optional[str] = None,
    is_primary: bool = True
) -> None:
    """
    Directly assign a role to a user (e.g., during onboarding).
    
    This is different from calculate_user_roles() which analyzes activity.
    Use this for explicit role assignments like "yeni_gelen" during onboarding.
    
    Args:
        user_id: UUID of the user
        role: Role name (must match user_role ENUM)
        city_key: Optional city_key for city-specific roles
        is_primary: If True, sets as primary_role; if False, sets as secondary_role
    
    Raises:
        Exception: If database operations fail
    """
    try:
        # Check if user already has a role record
        existing_sql = """
            SELECT primary_role, secondary_role
            FROM user_roles
            WHERE user_id = $1
        """
        existing_row = await fetchrow(existing_sql, user_id)
        
        if existing_row:
            # User already has a role record - update it
            existing_primary = existing_row.get("primary_role")
            existing_secondary = existing_row.get("secondary_role")
            
            if is_primary:
                # Set as primary, keep existing secondary if present
                new_primary = role
                new_secondary = existing_secondary
            else:
                # Set as secondary, keep existing primary
                new_primary = existing_primary
                new_secondary = role
            
            upsert_sql = """
                UPDATE user_roles
                SET 
                    primary_role = $1,
                    secondary_role = $2,
                    city_key = $3,
                    updated_at = NOW()
                WHERE user_id = $4
            """
            await execute(
                upsert_sql,
                new_primary,
                new_secondary,
                city_key,
                user_id,
            )
        else:
            # New role record - create it
            if is_primary:
                new_primary = role
                new_secondary = None
            else:
                # If setting as secondary but no primary exists, set as primary instead
                new_primary = role
                new_secondary = None
            
            insert_sql = """
                INSERT INTO user_roles (
                    user_id,
                    primary_role,
                    secondary_role,
                    city_key,
                    earned_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, NOW(), NOW()
                )
            """
            await execute(
                insert_sql,
                user_id,
                new_primary,
                new_secondary,
                city_key,
            )
        
        logger.info(
            f"Assigned role to user {user_id}: "
            f"role={role}, is_primary={is_primary}, city_key={city_key}"
        )
        
    except Exception as e:
        logger.error(
            f"Failed to assign role to user {user_id}: {e}",
            exc_info=True
        )
        raise


async def calculate_user_roles(user_id: UUID, city_key: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Calculate and assign roles for a user based on their activity.
    
    This function:
    1. Analyzes user activity (check-ins, Söz, poll responses)
    2. Determines primary and secondary roles based on activity patterns
    3. Updates the user_roles table
    
    Args:
        user_id: UUID of the user
        city_key: Optional city_key. If not provided, will be fetched from user_profiles.
    
    Returns:
        Tuple of (primary_role, secondary_role)
    
    Raises:
        Exception: If database operations fail
    """
    try:
        # Get city_key from user_profiles if not provided
        if city_key is None:
            city_key_sql = """
                SELECT city_key
                FROM user_profiles
                WHERE id = $1
            """
            city_row = await fetchrow(city_key_sql, user_id)
            if city_row:
                city_key = city_row.get("city_key")
        
        # Get activity summary (pre-aggregated metrics)
        summary_sql = """
            SELECT 
                last_4_weeks_active_days,
                total_söz_count,
                total_check_in_count,
                total_poll_response_count
            FROM user_activity_summary
            WHERE user_id = $1
        """
        summary_row = await fetchrow(summary_sql, user_id)
        
        # Default values if no summary exists
        last_4_weeks_active_days = 0
        total_söz_count = 0
        total_check_in_count = 0
        total_poll_response_count = 0
        
        if summary_row:
            last_4_weeks_active_days = int(summary_row.get("last_4_weeks_active_days", 0) or 0)
            total_söz_count = int(summary_row.get("total_söz_count", 0) or 0)
            total_check_in_count = int(summary_row.get("total_check_in_count", 0) or 0)
            total_poll_response_count = int(summary_row.get("total_poll_response_count", 0) or 0)
        
        # Calculate check-ins per week in last 4 weeks
        check_ins_per_week = 0
        if last_4_weeks_active_days > 0:
            # Approximate: if user was active 12+ days in last 4 weeks, that's ~3 days per week
            # More precise: count actual check-ins in last 4 weeks
            check_ins_4w_sql = """
                SELECT COUNT(*) as count
                FROM check_ins
                WHERE user_id = $1 
                AND created_at > NOW() - INTERVAL '4 weeks'
            """
            check_ins_row = await fetchrow(check_ins_4w_sql, user_id)
            check_ins_4w = int(check_ins_row.get("count", 0) or 0) if check_ins_row else 0
            check_ins_per_week = check_ins_4w / 4.0  # Average per week
        
        # Calculate Söz quality (average reactions per Söz)
        avg_reactions_per_soz = 0.0
        if total_söz_count > 0:
            reactions_sql = """
                SELECT COUNT(*) as reaction_count
                FROM location_reactions lr
                INNER JOIN location_notes ln ON lr.location_id = ln.location_id
                WHERE ln.user_id = $1
                AND ln.created_at > NOW() - INTERVAL '4 weeks'
            """
            reactions_row = await fetchrow(reactions_sql, user_id)
            reaction_count = int(reactions_row.get("reaction_count", 0) or 0) if reactions_row else 0
            avg_reactions_per_soz = reaction_count / float(total_söz_count) if total_söz_count > 0 else 0.0
        
        # Determine primary role
        primary_role = ROLE_YENI_GELEN  # Default for new users
        secondary_role: Optional[str] = None
        
        # Role assignment logic (order matters - more specific roles first)
        
        # 1. Mahalleli: Regular check-ins (3+ per week in last 4 weeks)
        if check_ins_per_week >= 3.0 and last_4_weeks_active_days >= 12:
            primary_role = ROLE_MAHALLELI
        
        # 2. Anlatıcı: Many Söz with positive feedback
        if total_söz_count >= 5 and avg_reactions_per_soz >= 2.0:
            if primary_role == ROLE_MAHALLELI:
                # If already mahalleli, make anlatıcı secondary
                secondary_role = ROLE_ANLATICI
            else:
                primary_role = ROLE_ANLATICI
        
        # 3. Ses Veren: Many poll responses
        if total_poll_response_count >= 10:
            if primary_role == ROLE_MAHALLELI or primary_role == ROLE_ANLATICI:
                secondary_role = ROLE_SES_VEREN
            else:
                primary_role = ROLE_SES_VEREN
        
        # 4. Sözü Dinlenir: Söz with high appreciation (many reactions)
        if total_söz_count >= 3 and avg_reactions_per_soz >= 5.0:
            if primary_role != ROLE_ANLATICI:
                # If not already anlatıcı, this can be primary or secondary
                if primary_role == ROLE_MAHALLELI:
                    secondary_role = ROLE_SOZU_DINLENIR
                else:
                    primary_role = ROLE_SOZU_DINLENIR
        
        # 5. Yerinde Tespit: Accurate observations (future: based on "useful" markers)
        # For now, this is not implemented - requires additional data
        
        # 6. Sessiz Güç: Many reads, few posts (future: requires view tracking)
        # For now, this is not implemented - requires view/read tracking
        
        # Update user_roles table
        upsert_sql = """
            INSERT INTO user_roles (
                user_id,
                primary_role,
                secondary_role,
                city_key,
                earned_at,
                updated_at
            ) VALUES (
                $1, $2, $3, $4, NOW(), NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                primary_role = EXCLUDED.primary_role,
                secondary_role = EXCLUDED.secondary_role,
                city_key = EXCLUDED.city_key,
                updated_at = NOW()
        """
        
        await execute(
            upsert_sql,
            user_id,
            primary_role,
            secondary_role,
            city_key,
        )
        
        logger.info(
            f"Calculated roles for user {user_id}: "
            f"primary={primary_role}, secondary={secondary_role}, "
            f"city={city_key}, check_ins/week={check_ins_per_week:.1f}, "
            f"söz={total_söz_count}, reactions/söz={avg_reactions_per_soz:.1f}, "
            f"polls={total_poll_response_count}"
        )
        
        return (primary_role, secondary_role)
        
    except Exception as e:
        logger.error(
            f"Failed to calculate roles for user {user_id}: {e}",
            exc_info=True
        )
        raise


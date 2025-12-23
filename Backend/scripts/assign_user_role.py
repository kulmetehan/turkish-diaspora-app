#!/usr/bin/env python3
"""
Assign a role to a specific user.

This is a utility script to manually assign a role to a user, useful for:
- Fixing missing roles for specific users
- Testing role assignment
- Admin operations

Usage:
    python -m scripts.assign_user_role --user-id <uuid> --role yeni_gelen
    python -m scripts.assign_user_role --user-id <uuid> --role yeni_gelen --city-key rotterdam
    python -m scripts.assign_user_role --user-id <uuid> --role yeni_gelen --city-key rotterdam --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.db_service import init_db_pool, fetchrow
from services.role_service import assign_role, ROLE_YENI_GELEN, ROLE_MAHALLELI
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()

# Valid roles
VALID_ROLES = {
    "yeni_gelen": ROLE_YENI_GELEN,
    "mahalleli": ROLE_MAHALLELI,
    # Add more as needed
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Assign a role to a specific user"
    )
    ap.add_argument(
        "--user-id",
        required=True,
        help="User ID (UUID) to assign role to"
    )
    ap.add_argument(
        "--role",
        required=True,
        help=f"Role to assign: {', '.join(VALID_ROLES.keys())}"
    )
    ap.add_argument(
        "--city-key",
        help="City key for the role (optional)"
    )
    ap.add_argument(
        "--primary",
        action="store_true",
        default=True,
        help="Assign as primary role (default: true)"
    )
    ap.add_argument(
        "--secondary",
        action="store_true",
        help="Assign as secondary role (overrides --primary)"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually assign the role, just show what would be done"
    )
    return ap.parse_args()


async def main_async() -> None:
    args = parse_args()
    
    # Validate and parse user_id
    try:
        user_id = UUID(args.user_id)
    except ValueError:
        print(f"ERROR: Invalid user ID format: {args.user_id}")
        print("User ID must be a valid UUID")
        sys.exit(1)
    
    # Validate role
    role_key = args.role.lower().strip()
    if role_key not in VALID_ROLES:
        print(f"ERROR: Invalid role: {args.role}")
        print(f"Valid roles: {', '.join(VALID_ROLES.keys())}")
        sys.exit(1)
    
    role = VALID_ROLES[role_key]
    city_key = args.city_key.strip().lower() if args.city_key else None
    is_primary = args.primary and not args.secondary
    dry_run = args.dry_run
    
    await init_db_pool()
    
    # Check if user exists
    check_user_sql = """
        SELECT id, display_name, onboarding_completed
        FROM user_profiles
        WHERE id = $1
    """
    user_row = await fetchrow(check_user_sql, user_id)
    
    if not user_row:
        print(f"ERROR: User not found: {user_id}")
        sys.exit(1)
    
    display_name = user_row.get("display_name") or "Unknown"
    onboarding_completed = user_row.get("onboarding_completed", False)
    
    print(f"\n[AssignRole] User: {user_id}")
    print(f"  - Display name: {display_name}")
    print(f"  - Onboarding completed: {onboarding_completed}")
    print(f"  - Role to assign: {role}")
    print(f"  - As: {'Primary' if is_primary else 'Secondary'}")
    print(f"  - City key: {city_key or 'None'}")
    
    # Check existing role
    existing_role_sql = """
        SELECT primary_role, secondary_role, city_key
        FROM user_roles
        WHERE user_id = $1
    """
    existing_row = await fetchrow(existing_role_sql, user_id)
    
    if existing_row:
        existing_primary = existing_row.get("primary_role")
        existing_secondary = existing_row.get("secondary_role")
        existing_city_key = existing_row.get("city_key")
        print(f"\n  Current roles:")
        print(f"    - Primary: {existing_primary or 'None'}")
        print(f"    - Secondary: {existing_secondary or 'None'}")
        print(f"    - City key: {existing_city_key or 'None'}")
    else:
        print(f"\n  Current roles: None")
    
    if dry_run:
        print(f"\n  → DRY RUN: Would assign {role} as {'primary' if is_primary else 'secondary'} role")
        if city_key:
            print(f"     with city_key: {city_key}")
        return
    
    try:
        await assign_role(
            user_id=user_id,
            role=role,
            city_key=city_key,
            is_primary=is_primary
        )
        
        # Verify role was assigned
        verify_sql = """
            SELECT primary_role, secondary_role, city_key
            FROM user_roles
            WHERE user_id = $1
        """
        verify_row = await fetchrow(verify_sql, user_id)
        
        if not verify_row:
            print(f"\n  ❌ ERROR: Role assignment failed - no role record found after assignment")
            logger.error(
                "assign_role_verification_failed",
                user_id=str(user_id),
                role=role
            )
            sys.exit(1)
        
        assigned_role = verify_row.get("primary_role") if is_primary else verify_row.get("secondary_role")
        
        if assigned_role == role:
            print(f"\n  ✅ Role assigned successfully!")
            print(f"     - Primary: {verify_row.get('primary_role') or 'None'}")
            print(f"     - Secondary: {verify_row.get('secondary_role') or 'None'}")
            print(f"     - City key: {verify_row.get('city_key') or 'None'}")
            logger.info(
                "assign_role_success",
                user_id=str(user_id),
                role=role,
                is_primary=is_primary,
                city_key=city_key
            )
        else:
            print(f"\n  ❌ ERROR: Role assignment verification failed")
            print(f"     Expected: {role} (as {'primary' if is_primary else 'secondary'})")
            print(f"     Got: {assigned_role}")
            logger.error(
                "assign_role_verification_failed",
                user_id=str(user_id),
                expected_role=role,
                actual_role=assigned_role,
                is_primary=is_primary
            )
            sys.exit(1)
    
    except Exception as e:
        print(f"\n  ❌ ERROR: Failed to assign role: {e}")
        logger.error(
            "assign_role_failed",
            user_id=str(user_id),
            role=role,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[AssignRole] Interrupted by user.")
    except Exception as e:
        print(f"\n[AssignRole] ERROR: {e}")
        logger.exception("assign_role_script_failed", error=str(e))
        raise


if __name__ == "__main__":
    main()



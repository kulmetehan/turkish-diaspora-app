#!/usr/bin/env python3
"""
Backfill missing roles for users who completed onboarding but don't have a role assigned.

This script identifies users who:
1. Have completed onboarding (onboarding_completed = true)
2. Don't have a role in user_roles table

And assigns them the "yeni_gelen" role.

Usage:
    python -m scripts.backfill_missing_roles
    python -m scripts.backfill_missing_roles --dry-run
    python -m scripts.backfill_missing_roles --limit 10
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

from services.db_service import init_db_pool, fetch, fetchrow
from services.role_service import assign_role, ROLE_YENI_GELEN
from app.core.logging import configure_logging, get_logger

configure_logging(service_name="script")
logger = get_logger()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Backfill missing roles for users who completed onboarding"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually assign roles, just show what would be done"
    )
    ap.add_argument(
        "--limit",
        type=int,
        help="Limit the number of users to process (default: no limit)"
    )
    return ap.parse_args()


async def main_async() -> None:
    args = parse_args()
    dry_run = args.dry_run
    limit = args.limit
    
    await init_db_pool()
    
    # Find users who completed onboarding but don't have a role
    sql = """
        SELECT 
            up.id as user_id,
            up.city_key,
            up.onboarding_completed_at,
            up.display_name
        FROM user_profiles up
        WHERE up.onboarding_completed = true
        AND up.id NOT IN (SELECT user_id FROM user_roles WHERE user_id IS NOT NULL)
        ORDER BY up.onboarding_completed_at ASC
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    users = await fetch(sql)
    
    if not users:
        print("✅ No users found without roles who completed onboarding.")
        return
    
    print(f"\n[BackfillRoles] Found {len(users)} user(s) without roles who completed onboarding")
    if dry_run:
        print("[BackfillRoles] DRY RUN MODE - No changes will be made\n")
    
    success_count = 0
    error_count = 0
    
    for user in users:
        user_id = UUID(str(user["user_id"]))
        city_key = user.get("city_key")
        display_name = user.get("display_name") or "Unknown"
        completed_at = user.get("onboarding_completed_at")
        
        print(f"\n[BackfillRoles] Processing user: {user_id}")
        print(f"  - Display name: {display_name}")
        print(f"  - City key: {city_key or 'None'}")
        print(f"  - Onboarding completed: {completed_at}")
        
        if dry_run:
            print(f"  → Would assign role: {ROLE_YENI_GELEN}")
            success_count += 1
            continue
        
        try:
            await assign_role(
                user_id=user_id,
                role=ROLE_YENI_GELEN,
                city_key=city_key,
                is_primary=True
            )
            
            # Verify role was assigned
            verify_sql = """
                SELECT primary_role FROM user_roles WHERE user_id = $1
            """
            verify_row = await fetchrow(verify_sql, user_id)
            
            if verify_row and verify_row.get("primary_role") == ROLE_YENI_GELEN:
                print(f"  ✅ Role assigned successfully: {ROLE_YENI_GELEN}")
                success_count += 1
                logger.info(
                    "backfill_role_assigned",
                    user_id=str(user_id),
                    role=ROLE_YENI_GELEN,
                    city_key=city_key
                )
            else:
                print(f"  ❌ Role assignment verification failed")
                error_count += 1
                logger.error(
                    "backfill_role_verification_failed",
                    user_id=str(user_id),
                    expected_role=ROLE_YENI_GELEN,
                    actual_role=verify_row.get("primary_role") if verify_row else None
                )
        
        except Exception as e:
            print(f"  ❌ Failed to assign role: {e}")
            error_count += 1
            logger.error(
                "backfill_role_assignment_failed",
                user_id=str(user_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
    
    print(f"\n[BackfillRoles] Summary:")
    print(f"  - Total processed: {len(users)}")
    print(f"  - Successful: {success_count}")
    print(f"  - Errors: {error_count}")
    
    if error_count > 0:
        sys.exit(1)


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[BackfillRoles] Interrupted by user.")
    except Exception as e:
        print(f"\n[BackfillRoles] ERROR: {e}")
        logger.exception("backfill_script_failed", error=str(e))
        raise


if __name__ == "__main__":
    main()


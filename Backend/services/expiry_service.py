# Backend/services/expiry_service.py
"""
Expiry service for managing expired claims.

Handles:
- Finding claims that have expired (free_until < NOW())
- Updating claim status to 'expired'
- Syncing status with locations.claimed_status
"""

from __future__ import annotations

from typing import List, Dict, Any

from app.core.logging import get_logger
from services.db_service import fetch, execute

logger = get_logger()


async def get_expired_claims() -> List[Dict[str, Any]]:
    """
    Get claims that have expired (free_until < NOW()).
    
    Returns:
        List of expired claim records, each dict contains:
        - id: token_location_claims.id
        - location_id: location ID
        - claim_status: current claim status
        - free_until: expiry date
    """
    sql = """
        SELECT 
            tlc.id,
            tlc.location_id,
            tlc.claim_status,
            tlc.free_until
        FROM token_location_claims tlc
        WHERE tlc.claim_status = 'claimed_free'
            AND tlc.free_until < NOW()
        ORDER BY tlc.free_until ASC
    """
    
    try:
        rows = await fetch(sql)
        
        if not rows:
            logger.debug("no_expired_claims")
            return []
        
        claims = []
        for row in rows:
            row_dict = dict(row)
            claims.append({
                "id": row_dict.get("id"),
                "location_id": row_dict.get("location_id"),
                "claim_status": row_dict.get("claim_status"),
                "free_until": row_dict.get("free_until"),
            })
        
        logger.info("expired_claims_found", count=len(claims))
        return claims
        
    except Exception as e:
        logger.error(
            "get_expired_claims_failed",
            error=str(e),
            exc_info=True,
        )
        raise


async def expire_claim(claim_id: int, location_id: int) -> bool:
    """
    Update claim status to 'expired' and sync with locations.claimed_status.
    
    Args:
        claim_id: Token location claim ID
        location_id: Location ID
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        # Use transaction to update both tables atomically
        from services.db_service import run_in_transaction, execute_with_conn
        
        async with run_in_transaction() as conn:
            # Update token_location_claims status
            await execute_with_conn(
                conn,
                """
                UPDATE token_location_claims
                SET claim_status = 'expired',
                    updated_at = NOW()
                WHERE id = $1
                """,
                claim_id,
            )
            
            # Sync with locations.claimed_status
            await execute_with_conn(
                conn,
                """
                UPDATE locations
                SET claimed_status = 'expired',
                    updated_at = NOW()
                WHERE id = $2
                """,
                location_id,
            )
        
        logger.info(
            "claim_expired",
            claim_id=claim_id,
            location_id=location_id,
        )
        return True
        
    except Exception as e:
        logger.error(
            "expire_claim_failed",
            claim_id=claim_id,
            location_id=location_id,
            error=str(e),
            exc_info=True,
        )
        return False


async def process_expired_claims(batch_size: int = 100) -> Dict[str, Any]:
    """
    Process expired claims and update their status.
    
    Args:
        batch_size: Maximum number of claims to process in one batch
        
    Returns:
        Dictionary with processing results:
        - total_found: Number of expired claims found
        - processed: Number of claims successfully processed
        - failed: Number of claims that failed to process
    """
    # Get expired claims
    claims = await get_expired_claims()
    
    if not claims:
        return {
            "total_found": 0,
            "processed": 0,
            "failed": 0,
        }
    
    # Limit batch size
    claims = claims[:batch_size]
    
    processed = 0
    failed = 0
    
    for claim in claims:
        claim_id = claim["id"]
        location_id = claim["location_id"]
        
        # Expire claim
        success = await expire_claim(claim_id, location_id)
        
        if success:
            processed += 1
        else:
            failed += 1
    
    result = {
        "total_found": len(claims),
        "processed": processed,
        "failed": failed,
    }
    
    logger.info(
        "expired_claims_processed",
        **result,
    )
    
    return result


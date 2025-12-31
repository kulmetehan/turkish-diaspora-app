# Backend/app/core/client_id.py
from __future__ import annotations

from uuid import UUID
from typing import Optional
from fastapi import Request, HTTPException


async def get_client_id(request: Request) -> Optional[str]:
    """
    Extract and validate client_id from X-Client-Id header.
    Returns None if header is missing or invalid UUID format.
    """
    client_id = request.headers.get("X-Client-Id")
    if not client_id:
        return None
    
    try:
        UUID(client_id)
        return client_id
    except ValueError:
        return None


async def require_client_id(request: Request) -> str:
    """
    Require client_id header, raise 400 if missing or invalid.
    """
    client_id = await get_client_id(request)
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="X-Client-Id header required (UUID format)"
        )
    return client_id


async def get_last_user_id(request: Request) -> Optional[str]:
    """
    Extract and validate last known user_id from X-Last-User-Id header.
    This is used to track poll responses even after user logs out.
    Returns None if header is missing or invalid UUID format.
    """
    last_user_id = request.headers.get("X-Last-User-Id")
    if not last_user_id:
        return None
    
    try:
        UUID(last_user_id)
        return last_user_id
    except ValueError:
        return None




























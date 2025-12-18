# Backend/app/deps/auth.py
from __future__ import annotations

from typing import Optional
from uuid import UUID

import jwt  # type: ignore
from fastapi import Header, HTTPException

from app.core.logging import logger
from app.config import require_supabase_jwt, settings

__all__ = ["User", "get_current_user", "get_current_user_optional"]


class User:
    """Authenticated user model."""
    def __init__(self, user_id: UUID, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


def extract_user_from_token(authorization: Optional[str]) -> Optional[User]:
    """
    Extract user information from Supabase JWT token.
    Returns User if valid, None if missing/invalid.
    """
    if not authorization or not str(authorization).startswith("Bearer "):
        return None
    
    token_only = str(authorization).split(" ", 1)[1].strip()
    
    secret = require_supabase_jwt()
    try:
        payload = jwt.decode(
            token_only,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )  # type: ignore[arg-type]
    except Exception as e:
        logger.debug("user_auth_token_invalid", error=str(e))
        return None
    
    # Extract user_id from 'sub' claim (Supabase user UUID)
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not sub:
        return None
    
    try:
        user_id = UUID(sub)
    except (ValueError, TypeError):
        logger.debug("user_auth_invalid_sub", sub=sub)
        return None
    
    email = payload.get("email") if isinstance(payload, dict) else None
    
    return User(user_id=user_id, email=email)


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """
    Required auth dependency - raises 401 if not authenticated.
    Use this for endpoints that require authentication.
    """
    user = extract_user_from_token(authorization)
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return user


async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[User]:
    """
    Optional auth dependency - returns None if not authenticated.
    Use this for endpoints that work for both authenticated and anonymous users.
    """
    return extract_user_from_token(authorization)




















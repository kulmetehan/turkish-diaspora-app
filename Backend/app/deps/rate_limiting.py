# Backend/app/deps/rate_limiting.py
"""
FastAPI dependencies for rate limiting.

Implements triple-layer rate limiting: client_id, user_id, and IP address.
All three must be under their respective limits for the request to proceed.
"""

from __future__ import annotations

from typing import Optional
from starlette.requests import Request
from fastapi import HTTPException, Depends

from app.core.client_id import get_client_id
from app.core.rate_limiting import check_and_increment_rate_limit
from app.core.rate_limits_config import get_rate_limit
from app.core.logging import get_logger
from app.deps.auth import get_current_user_optional, User

logger = get_logger()


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Checks X-Forwarded-For header first (for proxies/load balancers),
    then falls back to direct client IP.
    """
    # Check X-Forwarded-For header (from proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    # Last resort
    return "unknown"


def require_rate_limit_factory(action: str, limit: Optional[int] = None, window_seconds: Optional[int] = None):
    """
    Factory function that returns a rate limit dependency for a specific action.
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            request: Request,
            _rate_limit: None = Depends(require_rate_limit_factory("check_in")),
        ):
            ...
    """
    async def _rate_limit_check(
        request: Request,
        client_id: Optional[str] = Depends(get_client_id),
        current_user: Optional[User] = Depends(get_current_user_optional),
    ) -> None:
        """
        FastAPI dependency that enforces rate limiting.
        
        Implements triple-layer rate limiting:
        1. By client_id (if present)
        2. By user_id (if authenticated)
        3. By IP address
        
        All three must pass for the request to proceed. If any layer is over limit,
        raises HTTPException 429.
        """
        # Get default limits if not provided
        if limit is None or window_seconds is None:
            default_limit, default_window = get_rate_limit(action)
            check_limit = limit or default_limit
            check_window = window_seconds or default_window
        else:
            check_limit = limit
            check_window = window_seconds
        
        # Extract identifiers
        ip_address = get_client_ip(request)
        user_id = current_user.user_id if current_user else None
        
        # Check all three layers (triple layer rate limiting)
        checks = []
        
        # Layer 1: Client ID rate limiting
        if client_id:
            allowed_client = await check_and_increment_rate_limit(
                "client_id", client_id, action, check_limit, check_window
            )
            checks.append(("client_id", allowed_client))
        
        # Layer 2: User ID rate limiting (when authenticated)
        if user_id:
            allowed_user = await check_and_increment_rate_limit(
                "user_id", str(user_id), action, check_limit, check_window
            )
            checks.append(("user_id", allowed_user))
        
        # Layer 3: IP address rate limiting
        if ip_address and ip_address != "unknown":
            allowed_ip = await check_and_increment_rate_limit(
                "ip", ip_address, action, check_limit, check_window
            )
            checks.append(("ip", allowed_ip))
        
        # All checks must pass
        if checks:
            failed_checks = [layer for layer, allowed in checks if not allowed]
            if failed_checks:
                logger.warning(
                    "rate_limit_exceeded",
                    action=action,
                    failed_layers=failed_checks,
                    client_id=client_id,
                    user_id=str(user_id) if user_id else None,
                    ip=ip_address,
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for action '{action}'. Please try again later.",
                    headers={"Retry-After": str(check_window)},
                )
        
        # If we reach here, all rate limit checks passed
        # Note: We've already incremented counters in check_and_increment_rate_limit
        return None
    
    return _rate_limit_check

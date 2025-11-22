from __future__ import annotations

from typing import Optional

import jwt  # type: ignore
from fastapi import Header, HTTPException

from app.core.logging import logger
from app.core.auth import AdminUser
from app.config import (
    get_allowed_admin_emails,
    require_allowed_admin_emails,
    require_supabase_jwt,
    settings,
)

__all__ = ["AdminUser", "verify_admin_user"]


async def verify_admin_user(authorization: Optional[str] = Header(None)) -> AdminUser:
    """
    Validate Supabase JWT and enforce admin allowlist.
    Adds verbose debug logging to diagnose header presence and decode failures.
    """
    logger.info(
        "auth_debug_header",
        raw_auth_header=authorization,
        allowed_admins=get_allowed_admin_emails(),
        has_secret=bool(settings.SUPABASE_JWT_SECRET),
    )

    if not authorization or not str(authorization).startswith("Bearer "):
        logger.info("auth_missing_or_malformed")
        raise HTTPException(status_code=401, detail="missing bearer token")

    token_only = str(authorization).split(" ", 1)[1].strip()

    logger.info(
        "auth_debug_before_decode",
        token_prefix=token_only[:20] if token_only else None,
        token_len=len(token_only) if token_only else 0,
    )

    secret = require_supabase_jwt()
    try:
        # Supabase access tokens include an "aud": "authenticated".
        # Disable audience verification only; keep signature/expiry checks.
        payload = jwt.decode(
            token_only,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )  # type: ignore[arg-type]
    except Exception as e:  # broad to log any decode failure
        logger.info("auth_debug_decode_failed", error=str(e), has_secret=bool(secret))
        raise HTTPException(status_code=401, detail="invalid token")

    logger.info(
        "auth_debug_after_decode",
        decoded_keys=list(payload.keys()) if isinstance(payload, dict) else [],
        email_in_token=(payload.get("email") if isinstance(payload, dict) else None),
        sub_in_token=(payload.get("sub") if isinstance(payload, dict) else None),
    )

    email = payload.get("email") if isinstance(payload, dict) else None
    if not email:
        logger.info("auth_email_missing")
        raise HTTPException(status_code=401, detail="email missing in token")

    allowed = set(require_allowed_admin_emails())
    if email.lower() not in allowed:
        logger.info("auth_email_forbidden", email=email)
        raise HTTPException(status_code=403, detail="forbidden")

    return AdminUser(email=email)


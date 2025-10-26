from __future__ import annotations

from dataclasses import dataclass
from fastapi import HTTPException, Request
import jwt  # type: ignore

from app.config import settings
from app.core.logging import logger


@dataclass
class AdminUser:
    email: str


async def verify_admin_user(request: Request) -> AdminUser:
    """
    Validate Supabase JWT and enforce admin allowlist.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.info("auth_missing_or_malformed")
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])  # type: ignore[arg-type]
    except jwt.ExpiredSignatureError:  # type: ignore[attr-defined]
        logger.info("auth_token_expired")
        raise HTTPException(status_code=401, detail="token expired")
    except Exception:
        logger.info("auth_token_invalid")
        raise HTTPException(status_code=401, detail="invalid token")

    email = payload.get("email") if isinstance(payload, dict) else None
    if not email:
        logger.info("auth_email_missing")
        raise HTTPException(status_code=401, detail="email missing in token")

    allow_csv = settings.ALLOWED_ADMIN_EMAILS
    allowed = {e.strip().lower() for e in allow_csv.split(",") if e.strip()}
    if email.lower() not in allowed:
        logger.info("auth_email_forbidden", email=email)
        raise HTTPException(status_code=403, detail="forbidden")

    return AdminUser(email=email)



from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import verify_admin_user, AdminUser

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)


@router.get("/whoami")
async def who_am_i(admin: AdminUser = Depends(verify_admin_user)) -> dict:
    return {"ok": True, "admin_email": admin.email}



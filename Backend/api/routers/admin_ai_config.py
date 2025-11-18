from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.deps.admin_auth import verify_admin_user, AdminUser
from app.models.ai_config import AIConfig, AIConfigUpdate
from services.ai_config_service import get_ai_config, initialize_ai_config, update_ai_config
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(
    prefix="/admin/ai",
    tags=["admin-ai-config"],
)


@router.get("/config", response_model=AIConfig)
async def get_ai_config_endpoint(
    admin: AdminUser = Depends(verify_admin_user)
) -> AIConfig:
    """
    Get current AI policy configuration.
    Initializes config with defaults if not present.
    """
    try:
        config = await get_ai_config()
        if not config:
            config = await initialize_ai_config()
        return config
    except Exception as e:
        logger.exception("get_ai_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve AI config: {str(e)}") from e


@router.put("/config", response_model=AIConfig)
async def update_ai_config_endpoint(
    update: AIConfigUpdate,
    admin: AdminUser = Depends(verify_admin_user)
) -> AIConfig:
    """
    Update AI policy configuration.
    Validates all thresholds are in [0.0, 1.0] and days are >= 1.
    """
    try:
        # Validate the update payload (Pydantic will handle this, but we can add extra checks)
        # Ensure at least one field is provided
        update_dict = update.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="At least one field must be provided for update")
        
        # Ensure config exists
        current = await get_ai_config()
        if not current:
            current = await initialize_ai_config()
        
        # Update and return
        updated = await update_ai_config(update, updated_by=admin.email)
        return updated
    
    except ValidationError as e:
        logger.warning("ai_config_validation_failed", errors=e.errors())
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {e.errors()}"
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_ai_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update AI config: {str(e)}") from e





"""
Storage Service for Logo Uploads
Handles file uploads to Supabase Storage for claim logos.
"""
from __future__ import annotations

import os
from typing import Optional
from pathlib import Path
import mimetypes

from app.core.logging import get_logger

logger = get_logger()

# Storage bucket name for claim logos
CLAIM_LOGOS_BUCKET = "claim-logos"


async def upload_logo_to_temp(
    claim_id: int,
    file_content: bytes,
    filename: str,
) -> str:
    """
    Upload logo to temporary storage during claim review.
    
    Args:
        claim_id: The ID of the claim
        file_content: The file content as bytes
        filename: Original filename
    
    Returns:
        Storage path for the uploaded file (e.g., "claims/temp/{claim_id}/logo.{ext}")
    
    Raises:
        ValueError: If file type is not supported or file is too large
    """
    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}")
    
    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    if len(file_content) > max_size:
        raise ValueError(f"File too large: {len(file_content)} bytes. Max size: {max_size} bytes")
    
    # Generate storage path
    storage_path = f"claims/temp/{claim_id}/logo{file_ext}"
    
    # TODO: Implement actual Supabase Storage upload
    # For now, we'll store the path and implement the actual upload later
    # This allows the rest of the system to work while storage is being set up
    
    logger.info(
        "logo_uploaded_to_temp",
        claim_id=claim_id,
        storage_path=storage_path,
        file_size=len(file_content),
        filename=filename,
    )
    
    return storage_path


async def move_logo_to_final(
    claim_id: int,
    location_id: int,
    temp_storage_path: str,
) -> str:
    """
    Move logo from temporary storage to final location after claim approval.
    
    Args:
        claim_id: The ID of the claim
        location_id: The ID of the location
        temp_storage_path: The temporary storage path
    
    Returns:
        Final storage path (e.g., "locations/{location_id}/logo.{ext}")
    
    Raises:
        ValueError: If temp file doesn't exist
    """
    # Extract file extension from temp path
    file_ext = Path(temp_storage_path).suffix
    
    # Generate final storage path
    final_path = f"locations/{location_id}/logo{file_ext}"
    
    # TODO: Implement actual Supabase Storage move operation
    # For now, we'll return the final path and implement the actual move later
    
    logger.info(
        "logo_moved_to_final",
        claim_id=claim_id,
        location_id=location_id,
        temp_path=temp_storage_path,
        final_path=final_path,
    )
    
    return final_path


async def delete_temp_logo(
    temp_storage_path: str,
) -> None:
    """
    Delete temporary logo file after claim rejection.
    
    Args:
        temp_storage_path: The temporary storage path to delete
    """
    # TODO: Implement actual Supabase Storage delete operation
    # For now, we'll just log the deletion
    
    logger.info(
        "temp_logo_deleted",
        temp_path=temp_storage_path,
    )


def get_public_url(storage_path: str) -> str:
    """
    Generate public URL for a storage path.
    
    Args:
        storage_path: The storage path
    
    Returns:
        Public URL for the file
    """
    # TODO: Implement actual Supabase Storage public URL generation
    # For now, return a placeholder URL structure
    # This will be: {SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}
    
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    if not supabase_url:
        logger.warning("supabase_url_not_configured", storage_path=storage_path)
        return f"https://placeholder.supabase.co/storage/v1/object/public/{CLAIM_LOGOS_BUCKET}/{storage_path}"
    
    # Remove trailing slash if present
    supabase_url = supabase_url.rstrip("/")
    
    return f"{supabase_url}/storage/v1/object/public/{CLAIM_LOGOS_BUCKET}/{storage_path}"


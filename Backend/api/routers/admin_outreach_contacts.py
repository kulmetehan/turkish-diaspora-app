from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.deps.admin_auth import verify_admin_user, AdminUser
from services.db_service import fetch, execute, fetchrow
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/admin/outreach/contacts", tags=["admin-outreach-contacts"])


class AdminContactCreate(BaseModel):
    location_id: int = Field(..., description="Location ID")
    email: str = Field(..., regex=r'^[^\s@]+@[^\s@]+\.[^\s@]+$', description="Email address")
    confidence_score: int = Field(default=100, ge=0, le=100, description="Confidence score (0-100)")


class AdminContactResponse(BaseModel):
    id: int
    location_id: int
    location_name: Optional[str]
    email: str
    source: str
    confidence_score: int
    discovered_at: datetime
    created_at: datetime


@router.post("", response_model=AdminContactResponse, status_code=201)
async def create_outreach_contact(
    contact: AdminContactCreate,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Create a new outreach contact (admin only).
    
    Source will be set to 'manual' for admin-created contacts.
    """
    # Verify location exists
    location_row = await fetchrow(
        """
        SELECT id, name FROM locations WHERE id = $1
        """,
        contact.location_id,
    )
    
    if not location_row:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check for duplicate (UNIQUE constraint on location_id, email)
    existing_row = await fetchrow(
        """
        SELECT id FROM outreach_contacts
        WHERE location_id = $1 AND email = $2
        """,
        contact.location_id,
        contact.email.lower().strip(),
    )
    
    if existing_row:
        raise HTTPException(
            status_code=409,
            detail=f"Contact with email {contact.email} already exists for this location"
        )
    
    # Insert contact
    try:
        result = await fetchrow(
            """
            INSERT INTO outreach_contacts (location_id, email, source, confidence_score, discovered_at)
            VALUES ($1, $2, $3, $4, now())
            RETURNING id, location_id, email, source, confidence_score, discovered_at, created_at
            """,
            contact.location_id,
            contact.email.lower().strip(),
            "manual",
            contact.confidence_score,
        )
        
        logger.info(
            "admin_contact_created",
            admin_email=admin.email,
            contact_id=result["id"],
            location_id=contact.location_id,
            email=contact.email[:3] + "***"  # Log partially masked email
        )
        
        return AdminContactResponse(
            id=result["id"],
            location_id=result["location_id"],
            location_name=location_row.get("name"),
            email=result["email"],
            source=result["source"],
            confidence_score=result["confidence_score"],
            discovered_at=result["discovered_at"],
            created_at=result["created_at"],
        )
        
    except Exception as e:
        logger.error(
            "admin_contact_create_error",
            admin_email=admin.email,
            location_id=contact.location_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to create contact: {str(e)}")


@router.get("", response_model=List[AdminContactResponse])
async def list_outreach_contacts(
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List outreach contacts (admin only).
    """
    conditions = []
    params = []
    param_num = 1
    
    if location_id:
        conditions.append(f"oc.location_id = ${param_num}")
        params.append(location_id)
        param_num += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    params.append(limit)
    params.append(offset)
    
    sql = f"""
        SELECT 
            oc.id, oc.location_id, oc.email, oc.source,
            oc.confidence_score, oc.discovered_at, oc.created_at,
            l.name as location_name
        FROM outreach_contacts oc
        LEFT JOIN locations l ON l.id = oc.location_id
        {where_clause}
        ORDER BY oc.created_at DESC
        LIMIT ${param_num} OFFSET ${param_num + 1}
    """
    
    rows = await fetch(sql, *params)
    
    return [
        AdminContactResponse(
            id=row["id"],
            location_id=row["location_id"],
            location_name=row.get("location_name"),
            email=row["email"],
            source=row["source"],
            confidence_score=row["confidence_score"],
            discovered_at=row["discovered_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.delete("/{contact_id}", status_code=204)
async def delete_outreach_contact(
    contact_id: int = Path(..., description="Contact ID"),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Delete an outreach contact (admin only).
    """
    # Check if contact exists
    existing_row = await fetchrow(
        """
        SELECT id, location_id, email FROM outreach_contacts WHERE id = $1
        """,
        contact_id,
    )
    
    if not existing_row:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Delete contact
    await execute(
        """
        DELETE FROM outreach_contacts WHERE id = $1
        """,
        contact_id,
    )
    
    logger.info(
        "admin_contact_deleted",
        admin_email=admin.email,
        contact_id=contact_id,
        location_id=existing_row["location_id"],
        email=existing_row["email"][:3] + "***"  # Log partially masked email
    )


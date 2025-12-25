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
    email: str = Field(..., pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$', description="Email address")
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


class BulkDeleteRequest(BaseModel):
    contact_ids: List[int] = Field(..., min_items=1, description="List of contact IDs to delete")


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_outreach_contacts(
    request: BulkDeleteRequest,
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    Bulk delete outreach contacts (admin only).
    """
    deleted_count = 0
    failed_count = 0
    errors = []
    
    for contact_id in request.contact_ids:
        try:
            # Check if contact exists
            existing_row = await fetchrow(
                """
                SELECT id, location_id, email FROM outreach_contacts WHERE id = $1
                """,
                contact_id,
            )
            
            if not existing_row:
                failed_count += 1
                errors.append(f"Contact {contact_id} not found")
                continue
            
            # Delete contact
            await execute(
                """
                DELETE FROM outreach_contacts WHERE id = $1
                """,
                contact_id,
            )
            
            deleted_count += 1
            logger.info(
                "admin_contact_deleted",
                admin_email=admin.email,
                contact_id=contact_id,
                location_id=existing_row["location_id"],
                email=existing_row["email"][:3] + "***"  # Log partially masked email
            )
        except Exception as e:
            failed_count += 1
            error_msg = f"Failed to delete contact {contact_id}: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "admin_contact_bulk_delete_error",
                admin_email=admin.email,
                contact_id=contact_id,
                error=str(e),
                exc_info=True
            )
    
    logger.info(
        "admin_contacts_bulk_deleted",
        admin_email=admin.email,
        total_requested=len(request.contact_ids),
        deleted_count=deleted_count,
        failed_count=failed_count
    )
    
    return BulkDeleteResponse(
        deleted_count=deleted_count,
        failed_count=failed_count,
        errors=errors
    )


class LocationWithoutContact(BaseModel):
    id: int
    name: Optional[str]
    address: Optional[str]
    category: Optional[str]
    state: str


class LocationsWithoutContactResponse(BaseModel):
    items: List[LocationWithoutContact]
    total: int
    limit: int
    offset: int


@router.get("/locations-without-contact", response_model=LocationsWithoutContactResponse)
async def list_locations_without_contact(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_user),
):
    """
    List verified locations that don't have a contact yet (admin only).
    Returns paginated results with total count.
    """
    # Get total count
    count_sql = """
        SELECT COUNT(*)::int AS total
        FROM locations l
        WHERE l.state = 'VERIFIED'
          AND (l.is_retired = false OR l.is_retired IS NULL)
          AND (l.confidence_score IS NOT NULL AND l.confidence_score >= 0.80)
          AND l.lat IS NOT NULL
          AND l.lng IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 
              FROM outreach_contacts oc 
              WHERE oc.location_id = l.id
          )
    """
    count_row = await fetchrow(count_sql)
    total = int(count_row["total"]) if count_row else 0
    
    # Get paginated results
    params = [limit, offset]
    sql = """
        SELECT 
            l.id,
            l.name,
            l.address,
            l.category,
            l.state
        FROM locations l
        WHERE l.state = 'VERIFIED'
          AND (l.is_retired = false OR l.is_retired IS NULL)
          AND (l.confidence_score IS NOT NULL AND l.confidence_score >= 0.80)
          AND l.lat IS NOT NULL
          AND l.lng IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 
              FROM outreach_contacts oc 
              WHERE oc.location_id = l.id
          )
        ORDER BY l.last_verified_at DESC NULLS LAST, l.id DESC
        LIMIT $1 OFFSET $2
    """
    
    rows = await fetch(sql, *params)
    
    return LocationsWithoutContactResponse(
        items=[
            LocationWithoutContact(
                id=row["id"],
                name=row.get("name"),
                address=row.get("address"),
                category=row.get("category"),
                state=row["state"],
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


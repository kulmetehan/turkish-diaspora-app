from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

from app.deps.auth import get_current_user, User
from app.core.feature_flags import require_feature
from services.db_service import fetch, execute
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/business/accounts", tags=["business-accounts"])


class BusinessAccountCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    vat_kvk: Optional[str] = Field(None, max_length=50)
    country: str = Field(default="NL", max_length=2)
    website: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)


class BusinessAccountUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    vat_kvk: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=2)
    website: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)


class BusinessAccountResponse(BaseModel):
    id: int
    owner_user_id: UUID
    company_name: str
    vat_kvk: Optional[str]
    country: str
    website: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    subscription_tier: str
    subscription_status: str
    created_at: datetime
    updated_at: datetime


class BusinessMemberResponse(BaseModel):
    id: int
    user_id: UUID
    role: str
    created_at: datetime


class BusinessMemberCreate(BaseModel):
    user_id: UUID
    role: str = Field(default="editor", pattern="^(owner|admin|editor)$")


@router.post("", response_model=BusinessAccountResponse, status_code=201)
async def create_business_account(
    account: BusinessAccountCreate,
    user: User = Depends(get_current_user),
):
    """
    Create a new business account for the authenticated user.
    User can only have one business account.
    """
    require_feature("business_accounts_enabled")
    
    # Check if user already has a business account
    check_sql = """
        SELECT id FROM business_accounts WHERE owner_user_id = $1
    """
    existing = await fetch(check_sql, user.user_id)
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail="User already has a business account"
        )
    
    # Create business account
    insert_sql = """
        INSERT INTO business_accounts (
            owner_user_id, company_name, vat_kvk, country,
            website, contact_email, contact_phone,
            subscription_tier, subscription_status,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'basic', 'active', now(), now())
        RETURNING 
            id, owner_user_id, company_name, vat_kvk, country,
            website, contact_email, contact_phone,
            subscription_tier, subscription_status,
            created_at, updated_at
    """
    
    result = await fetch(
        insert_sql,
        user.user_id,
        account.company_name,
        account.vat_kvk,
        account.country,
        account.website,
        account.contact_email,
        account.contact_phone,
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create business account")
    
    row = result[0]
    
    logger.info(
        "business_account_created",
        account_id=row["id"],
        user_id=str(user.user_id),
        company_name=account.company_name,
    )
    
    return BusinessAccountResponse(**row)


@router.get("/me", response_model=BusinessAccountResponse)
async def get_my_business_account(
    user: User = Depends(get_current_user),
):
    """
    Get the authenticated user's business account.
    """
    require_feature("business_accounts_enabled")
    
    sql = """
        SELECT 
            id, owner_user_id, company_name, vat_kvk, country,
            website, contact_email, contact_phone,
            subscription_tier, subscription_status,
            created_at, updated_at
        FROM business_accounts
        WHERE owner_user_id = $1
        LIMIT 1
    """
    
    rows = await fetch(sql, user.user_id)
    
    if not rows:
        raise HTTPException(status_code=404, detail="Business account not found")
    
    return BusinessAccountResponse(**rows[0])


@router.put("/{account_id}", response_model=BusinessAccountResponse)
async def update_business_account(
    account_id: int = Path(..., description="Business account ID"),
    update: BusinessAccountUpdate = ...,
    user: User = Depends(get_current_user),
):
    """
    Update business account. Only the owner can update.
    """
    require_feature("business_accounts_enabled")
    
    # Verify ownership
    check_sql = """
        SELECT owner_user_id FROM business_accounts WHERE id = $1
    """
    account_rows = await fetch(check_sql, account_id)
    
    if not account_rows:
        raise HTTPException(status_code=404, detail="Business account not found")
    
    if account_rows[0]["owner_user_id"] != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the account owner can update this business account"
        )
    
    # Build update SQL dynamically
    updates = []
    values = []
    param_num = 1
    
    if update.company_name is not None:
        updates.append(f"company_name = ${param_num}")
        values.append(update.company_name)
        param_num += 1
    
    if update.vat_kvk is not None:
        updates.append(f"vat_kvk = ${param_num}")
        values.append(update.vat_kvk)
        param_num += 1
    
    if update.country is not None:
        updates.append(f"country = ${param_num}")
        values.append(update.country)
        param_num += 1
    
    if update.website is not None:
        updates.append(f"website = ${param_num}")
        values.append(update.website)
        param_num += 1
    
    if update.contact_email is not None:
        updates.append(f"contact_email = ${param_num}")
        values.append(update.contact_email)
        param_num += 1
    
    if update.contact_phone is not None:
        updates.append(f"contact_phone = ${param_num}")
        values.append(update.contact_phone)
        param_num += 1
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = now()")
    values.append(account_id)
    
    update_sql = f"""
        UPDATE business_accounts
        SET {', '.join(updates)}
        WHERE id = ${param_num}
        RETURNING 
            id, owner_user_id, company_name, vat_kvk, country,
            website, contact_email, contact_phone,
            subscription_tier, subscription_status,
            created_at, updated_at
    """
    
    result = await fetch(update_sql, *values)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update business account")
    
    logger.info(
        "business_account_updated",
        account_id=account_id,
        user_id=str(user.user_id),
    )
    
    return BusinessAccountResponse(**result[0])


@router.get("/{account_id}/members", response_model=List[BusinessMemberResponse])
async def list_business_members(
    account_id: int = Path(..., description="Business account ID"),
    user: User = Depends(get_current_user),
):
    """
    List members of a business account.
    Only accessible by account owner or members.
    """
    require_feature("business_accounts_enabled")
    
    # Check if user is owner or member
    check_sql = """
        SELECT 1 FROM business_accounts
        WHERE id = $1 AND owner_user_id = $2
        UNION ALL
        SELECT 1 FROM business_members
        WHERE business_account_id = $1 AND user_id = $2
        LIMIT 1
    """
    access_rows = await fetch(check_sql, account_id, user.user_id)
    
    if not access_rows:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You must be the owner or a member of this business account."
        )
    
    sql = """
        SELECT id, user_id, role, created_at
        FROM business_members
        WHERE business_account_id = $1
        ORDER BY created_at ASC
    """
    
    rows = await fetch(sql, account_id)
    
    return [BusinessMemberResponse(**row) for row in rows]


@router.post("/{account_id}/members", response_model=BusinessMemberResponse, status_code=201)
async def add_business_member(
    account_id: int = Path(..., description="Business account ID"),
    member: BusinessMemberCreate = ...,
    user: User = Depends(get_current_user),
):
    """
    Add a member to a business account.
    Only the owner can add members.
    """
    require_feature("business_accounts_enabled")
    
    # Verify ownership
    check_sql = """
        SELECT owner_user_id FROM business_accounts WHERE id = $1
    """
    account_rows = await fetch(check_sql, account_id)
    
    if not account_rows:
        raise HTTPException(status_code=404, detail="Business account not found")
    
    if account_rows[0]["owner_user_id"] != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the account owner can add members"
        )
    
    # Prevent adding owner as member
    if account_rows[0]["owner_user_id"] == member.user_id:
        raise HTTPException(
            status_code=400,
            detail="Owner cannot be added as a member"
        )
    
    # Check if member already exists
    existing_sql = """
        SELECT id FROM business_members
        WHERE business_account_id = $1 AND user_id = $2
    """
    existing_rows = await fetch(existing_sql, account_id, member.user_id)
    
    if existing_rows:
        raise HTTPException(
            status_code=409,
            detail="User is already a member of this business account"
        )
    
    # Add member
    insert_sql = """
        INSERT INTO business_members (business_account_id, user_id, role, created_at)
        VALUES ($1, $2, $3, now())
        RETURNING id, user_id, role, created_at
    """
    
    result = await fetch(insert_sql, account_id, member.user_id, member.role)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add member")
    
    logger.info(
        "business_member_added",
        account_id=account_id,
        member_user_id=str(member.user_id),
        role=member.role,
        added_by=str(user.user_id),
    )
    
    return BusinessMemberResponse(**result[0])


@router.delete("/{account_id}/members/{user_id}", status_code=204)
async def remove_business_member(
    account_id: int = Path(..., description="Business account ID"),
    user_id: UUID = Path(..., description="User ID to remove"),
    user: User = Depends(get_current_user),
):
    """
    Remove a member from a business account.
    Only the owner can remove members.
    """
    require_feature("business_accounts_enabled")
    
    # Verify ownership
    check_sql = """
        SELECT owner_user_id FROM business_accounts WHERE id = $1
    """
    account_rows = await fetch(check_sql, account_id)
    
    if not account_rows:
        raise HTTPException(status_code=404, detail="Business account not found")
    
    if account_rows[0]["owner_user_id"] != user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the account owner can remove members"
        )
    
    # Remove member
    delete_sql = """
        DELETE FROM business_members
        WHERE business_account_id = $1 AND user_id = $2
        RETURNING id
    """
    
    result = await fetch(delete_sql, account_id, user_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Member not found in this business account"
        )
    
    logger.info(
        "business_member_removed",
        account_id=account_id,
        removed_user_id=str(user_id),
        removed_by=str(user.user_id),
    )
    
    return {"ok": True}














# Backend/api/routers/contact.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from starlette.requests import Request

from app.core.logging import logger
from services.db_service import execute, fetchrow
from services.email_service import get_email_service

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactFormRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    message: str = Field(..., min_length=1, max_length=1000)

    @field_validator("email", "phone")
    @classmethod
    def validate_contact_info(cls, v, info):
        # At least one of email or phone must be provided
        if info.field_name == "email":
            return v
        elif info.field_name == "phone":
            return v
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class ContactFormResponse(BaseModel):
    ok: bool
    message: str
    submission_id: Optional[int] = None


@router.post("", response_model=ContactFormResponse)
async def submit_contact_form(
    request: ContactFormRequest,
    http_request: Request,
):
    """Submit contact form. At least email or phone must be provided."""
    
    # Validate that at least email or phone is provided
    if not request.email and not request.phone:
        raise HTTPException(
            status_code=400,
            detail="Email of telefoonnummer is verplicht"
        )
    
    # Get client IP for logging
    client_ip = http_request.client.host if http_request.client else None
    
    try:
        # Insert into database
        insert_sql = """
            INSERT INTO contact_submissions (
                name, email, phone, message, created_at, status
            ) VALUES (
                $1, $2, $3, $4, now(), 'new'
            ) RETURNING id
        """
        
        row = await fetchrow(
            insert_sql,
            request.name,
            request.email,
            request.phone,
            request.message,
        )
        
        submission_id = row["id"] if row else None
        
        # Send email notification to admin
        try:
            email_service = get_email_service()
            
            # Get admin email from environment or use default
            admin_email = "info@turkspot.app"  # TODO: Move to config
            
            context = {
                "name": request.name,
                "email": request.email or "Niet opgegeven",
                "phone": request.phone or "Niet opgegeven",
                "message": request.message,
                "submission_id": submission_id,
                "submitted_at": datetime.utcnow().isoformat(),
                "client_ip": client_ip or "Onbekend",
            }
            
            html_body, text_body = email_service.render_template("contact_form", context)
            
            await email_service.send_email(
                to_email=admin_email,
                subject=f"Nieuw contactformulier bericht van {request.name}",
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "contact_form_submitted",
                submission_id=submission_id,
                name=request.name,
                has_email=bool(request.email),
                has_phone=bool(request.phone),
            )
        except Exception as e:
            # Log error but don't fail the request
            logger.error(
                "contact_form_email_failed",
                submission_id=submission_id,
                error=str(e),
                exc_info=True,
            )
        
        return ContactFormResponse(
            ok=True,
            message="Bericht verzonden! We nemen zo snel mogelijk contact met je op.",
            submission_id=submission_id,
        )
        
    except Exception as e:
        logger.error(
            "contact_form_submission_failed",
            error=str(e),
            name=request.name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Kon bericht niet verzenden. Probeer het later opnieuw."
        )






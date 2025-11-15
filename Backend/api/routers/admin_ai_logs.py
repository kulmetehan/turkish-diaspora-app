from __future__ import annotations

import json
from datetime import datetime
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_ai_logs import AILogItem, AILogsResponse
from services.ai_explanation import generate_ai_explanation
from services.db_service import fetch, fetchrow


router = APIRouter(
    prefix="/admin/ai",
    tags=["admin-ai"],
)


@router.get("/logs", response_model=AILogsResponse)
async def get_ai_logs(
    location_id: Optional[int] = Query(default=None, description="Filter by location ID"),
    action_type: Optional[str] = Query(default=None, description="Filter by action type"),
    since: Optional[str] = Query(default=None, description="Filter by timestamp (ISO format)"),
    limit: int = Query(default=20, ge=1, le=200, description="Number of items per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    admin: AdminUser = Depends(verify_admin_user),
) -> AILogsResponse:
    """
    Retrieve AI decision logs with optional filtering.
    
    Returns paginated list of AI log entries with human-readable explanations.
    """
    # Build WHERE clause dynamically
    filters: List[str] = []
    params: List[Any] = []
    param_idx = 1
    
    if location_id is not None:
        filters.append(f"location_id = ${param_idx}")
        params.append(location_id)
        param_idx += 1
    
    if action_type:
        filters.append(f"action_type = ${param_idx}")
        params.append(action_type)
        param_idx += 1
    
    if since:
        try:
            # Parse ISO timestamp
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            filters.append(f"created_at >= ${param_idx}")
            params.append(since_dt)
            param_idx += 1
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'since' timestamp format. Use ISO format.")
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    
    # Build main query
    limit_param = param_idx
    offset_param = param_idx + 1
    params.extend([limit, offset])
    
    query = f"""
        SELECT 
            id,
            location_id,
            action_type,
            model_used,
            validated_output,
            is_success,
            error_message,
            created_at
        FROM ai_logs
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${limit_param} OFFSET ${offset_param}
    """
    
    rows = await fetch(query, *params)
    
    # Count total matching records
    count_query = f"""
        SELECT COUNT(1) AS total
        FROM ai_logs
        WHERE {where_clause}
    """
    count_params = params[:-2]  # Exclude limit and offset
    count_row = await fetchrow(count_query, *count_params)
    total = int(dict(count_row).get("total", 0)) if count_row else 0
    
    # Process rows and generate explanations
    items: List[AILogItem] = []
    for row in rows:
        row_dict = dict(row)
        
        # Safely parse validated_output: handle both dict and JSON string
        raw_validated = row_dict.get("validated_output")
        parsed_validated: Optional[Dict[str, Any]] = None
        
        if isinstance(raw_validated, dict):
            parsed_validated = raw_validated
        elif isinstance(raw_validated, str) and raw_validated.strip():
            # Handle JSON stored as text (legacy format)
            try:
                parsed = json.loads(raw_validated)
                if isinstance(parsed, dict):
                    parsed_validated = parsed
            except JSONDecodeError:
                # Leave parsed_validated as None if JSON parsing fails
                parsed_validated = None
        
        # Extract category and confidence_score from parsed validated_output if available
        category = None
        confidence_score = None
        
        if parsed_validated:
            category = parsed_validated.get("category")
            confidence_score = parsed_validated.get("confidence_score") or parsed_validated.get("confidence")
            # Normalize confidence to float if present
            if confidence_score is not None:
                try:
                    confidence_score = float(confidence_score)
                except (ValueError, TypeError):
                    confidence_score = None
        
        # Generate explanation using the parsed validated_output
        explanation_row_dict = {**row_dict, "validated_output": parsed_validated}
        explanation = generate_ai_explanation(explanation_row_dict)
        
        items.append(
            AILogItem(
                id=row_dict["id"],
                location_id=row_dict.get("location_id"),
                action_type=row_dict["action_type"],
                model_used=row_dict.get("model_used"),
                confidence_score=confidence_score,
                category=category,
                created_at=row_dict["created_at"],
                validated_output=parsed_validated,
                is_success=row_dict.get("is_success", True),
                error_message=row_dict.get("error_message"),
                explanation=explanation,
            )
        )
    
    return AILogsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


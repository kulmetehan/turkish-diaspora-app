from __future__ import annotations

import json
from datetime import datetime
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_ai_logs import AILogDetail, AILogItem, AILogsResponse
from services.ai_explanation import generate_ai_explanation
from services.db_service import fetch, fetchrow


router = APIRouter(
    prefix="/admin/ai",
    tags=["admin-ai"],
)


def _coerce_json_object(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except JSONDecodeError:
                return value
    return value


@router.get("/logs", response_model=AILogsResponse)
async def get_ai_logs(
    location_id: Optional[int] = Query(default=None, description="Filter by location ID"),
    action_type: Optional[str] = Query(default=None, description="Filter by action type"),
    since: Optional[str] = Query(default=None, description="Filter by timestamp (ISO format)"),
    news_only: bool = Query(default=False, description="Only include news-related AI logs"),
    news_id: Optional[int] = Query(default=None, description="Filter by news item ID"),
    source_key: Optional[str] = Query(default=None, description="Filter by news source key"),
    source_name: Optional[str] = Query(default=None, description="Filter by news source name"),
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
    table_alias = "ai"
    
    normalized_source_key = source_key.strip() if source_key else None
    normalized_source_name = source_name.strip() if source_name else None
    news_filters_active = bool(
        news_only
        or news_id is not None
        or normalized_source_key
        or normalized_source_name
    )
    
    if location_id is not None:
        filters.append(f"{table_alias}.location_id = ${param_idx}")
        params.append(location_id)
        param_idx += 1
    
    if action_type:
        filters.append(f"{table_alias}.action_type = ${param_idx}")
        params.append(action_type)
        param_idx += 1
    
    if since:
        try:
            # Parse ISO timestamp
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            filters.append(f"{table_alias}.created_at >= ${param_idx}")
            params.append(since_dt)
            param_idx += 1
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'since' timestamp format. Use ISO format.")
    
    if news_only:
        filters.append(f"{table_alias}.news_id IS NOT NULL")
        filters.append(f"{table_alias}.action_type LIKE 'news.%'")
    
    if news_id is not None:
        filters.append(f"{table_alias}.news_id = ${param_idx}")
        params.append(news_id)
        param_idx += 1
    
    if normalized_source_key:
        filters.append(f"rin.source_key = ${param_idx}")
        params.append(normalized_source_key)
        param_idx += 1
        news_filters_active = True
    
    if normalized_source_name:
        filters.append(f"rin.source_name = ${param_idx}")
        params.append(normalized_source_name)
        param_idx += 1
        news_filters_active = True
    
    where_clause = " AND ".join(filters) if filters else "1=1"
    
    join_clause = ""
    select_news_columns = ""
    if news_filters_active:
        join_clause = "LEFT JOIN raw_ingested_news rin ON rin.id = ai.news_id"
        select_news_columns = ", rin.source_key AS news_source_key, rin.source_name AS news_source_name"
    
    # Build main query
    limit_param = param_idx
    offset_param = param_idx + 1
    params.extend([limit, offset])
    
    query = f"""
        SELECT 
            {table_alias}.id,
            {table_alias}.location_id,
            {table_alias}.news_id,
            {table_alias}.action_type,
            {table_alias}.model_used,
            {table_alias}.validated_output,
            {table_alias}.is_success,
            {table_alias}.error_message,
            {table_alias}.created_at
            {select_news_columns}
        FROM ai_logs {table_alias}
        {join_clause}
        WHERE {where_clause}
        ORDER BY {table_alias}.created_at DESC
        LIMIT ${limit_param} OFFSET ${offset_param}
    """
    
    rows = await fetch(query, *params)
    
    # Count total matching records
    count_query = f"""
        SELECT COUNT(1) AS total
        FROM ai_logs {table_alias}
        {join_clause}
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
                news_id=row_dict.get("news_id"),
                action_type=row_dict["action_type"],
                model_used=row_dict.get("model_used"),
                confidence_score=confidence_score,
                category=category,
                created_at=row_dict["created_at"],
                validated_output=parsed_validated,
                is_success=row_dict.get("is_success", True),
                error_message=row_dict.get("error_message"),
                explanation=explanation,
                news_source_key=row_dict.get("news_source_key"),
                news_source_name=row_dict.get("news_source_name"),
            )
        )
    
    return AILogsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/logs/{log_id}", response_model=AILogDetail)
async def get_ai_log_detail(
    log_id: int,
    admin: AdminUser = Depends(verify_admin_user),
) -> AILogDetail:
    """
    Retrieve full prompt/response payload for a single AI log entry.
    """
    row = await fetchrow(
        """
        SELECT
            ai.id,
            ai.location_id,
            ai.news_id,
            ai.action_type,
            ai.model_used,
            ai.prompt,
            ai.raw_response,
            ai.validated_output,
            ai.is_success,
            ai.error_message,
            ai.created_at,
            rin.source_key AS news_source_key,
            rin.source_name AS news_source_name,
            rin.title AS news_title
        FROM ai_logs ai
        LEFT JOIN raw_ingested_news rin ON rin.id = ai.news_id
        WHERE ai.id = $1
        """,
        log_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="AI log not found")
    
    row_dict = dict(row)
    return AILogDetail(
        id=row_dict["id"],
        location_id=row_dict.get("location_id"),
        news_id=row_dict.get("news_id"),
        action_type=row_dict["action_type"],
        model_used=row_dict.get("model_used"),
        prompt=_coerce_json_object(row_dict.get("prompt")),
        raw_response=_coerce_json_object(row_dict.get("raw_response")),
        validated_output=_coerce_json_object(row_dict.get("validated_output")),
        is_success=row_dict.get("is_success", True),
        error_message=row_dict.get("error_message"),
        created_at=row_dict["created_at"],
        news_source_key=row_dict.get("news_source_key"),
        news_source_name=row_dict.get("news_source_name"),
        news_title=row_dict.get("news_title"),
    )


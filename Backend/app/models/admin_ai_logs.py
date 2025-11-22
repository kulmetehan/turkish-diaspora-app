from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AILogItem(BaseModel):
    """Single AI log entry for admin API response."""
    
    id: int
    location_id: Optional[int]
    news_id: Optional[int] = None
    action_type: str
    model_used: Optional[str]
    confidence_score: Optional[float] = None
    category: Optional[str] = None
    created_at: datetime
    validated_output: Optional[Dict[str, Any]] = None
    is_success: bool
    error_message: Optional[str] = None
    explanation: str
    news_source_key: Optional[str] = None
    news_source_name: Optional[str] = None


class AILogsResponse(BaseModel):
    """Paginated response for AI logs endpoint."""
    
    items: List[AILogItem]
    total: int
    limit: int
    offset: int


class AILogDetail(BaseModel):
    """Detailed AI log entry including raw prompt/response."""
    
    id: int
    location_id: Optional[int] = None
    news_id: Optional[int] = None
    action_type: str
    model_used: Optional[str] = None
    prompt: Optional[Any] = None
    raw_response: Optional[Any] = None
    validated_output: Optional[Any] = None
    is_success: bool
    error_message: Optional[str] = None
    created_at: datetime
    news_source_key: Optional[str] = None
    news_source_name: Optional[str] = None
    news_title: Optional[str] = None


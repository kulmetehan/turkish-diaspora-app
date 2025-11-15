from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AILogItem(BaseModel):
    """Single AI log entry for admin API response."""
    
    id: int
    location_id: Optional[int]
    action_type: str
    model_used: Optional[str]
    confidence_score: Optional[float] = None
    category: Optional[str] = None
    created_at: datetime
    validated_output: Optional[Dict[str, Any]] = None
    is_success: bool
    error_message: Optional[str] = None
    explanation: str


class AILogsResponse(BaseModel):
    """Paginated response for AI logs endpoint."""
    
    items: List[AILogItem]
    total: int
    limit: int
    offset: int


from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class TaskItem(BaseModel):
    """Individual task item in the response."""

    id: int
    task_type: str
    status: str
    created_at: datetime
    last_attempted_at: Optional[datetime] = None
    location_id: Optional[int] = None
    attempts: int = 0
    payload: Optional[Dict] = None


class TaskSummary(BaseModel):
    """Summary counts per status for a task type."""

    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0


class TasksResponse(BaseModel):
    """Response shape for GET /admin/tasks."""

    summary: Dict[str, TaskSummary]  # keyed by task_type
    items: List[TaskItem]
    total: int
    limit: int
    offset: int


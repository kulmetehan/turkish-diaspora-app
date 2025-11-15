from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps.admin_auth import AdminUser, verify_admin_user
from app.models.admin_tasks import TaskItem, TaskSummary, TasksResponse
from app.core.logging import get_logger
from services.db_service import fetch

router = APIRouter(
    prefix="/admin/tasks",
    tags=["admin-tasks"],
)

logger = get_logger()


@router.get("", response_model=TasksResponse)
async def list_tasks(
    task_type: Optional[str] = Query(default=None, description="Filter by task type (e.g., VERIFICATION)"),
    status: Optional[str] = Query(default=None, description="Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)"),
    since: Optional[str] = Query(default=None, description="ISO timestamp; only tasks created_at >= since"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of results per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    admin: AdminUser = Depends(verify_admin_user),
) -> TasksResponse:
    """
    List tasks with optional filtering and pagination.
    Returns summary counts per task_type and a paginated list of tasks.
    """
    # Parse since timestamp if provided
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail="Invalid 'since' timestamp format. Use ISO 8601 format.",
            )

    # Normalize status to uppercase
    status_val = None
    if status:
        status_upper = status.strip().upper()
        if status_upper in ("PENDING", "PROCESSING", "COMPLETED", "FAILED"):
            status_val = status_upper
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: PENDING, PROCESSING, COMPLETED, FAILED",
            )

    # Normalize task_type to uppercase
    task_type_val = None
    if task_type:
        task_type_val = task_type.strip().upper()

    try:
        # Build parameterized query strings with $1, $2, etc.
        where_parts: List[str] = []
        filter_params: List[Any] = []
        
        if task_type_val:
            param_num = len(filter_params) + 1
            where_parts.append(f"task_type = ${param_num}")
            filter_params.append(task_type_val)

        if status_val:
            param_num = len(filter_params) + 1
            where_parts.append(f"UPPER(status) = ${param_num}")
            filter_params.append(status_val)

        if since_dt:
            param_num = len(filter_params) + 1
            where_parts.append(f"created_at >= ${param_num}")
            filter_params.append(since_dt)

        where_sql = " AND ".join(where_parts) if where_parts else "1=1"

        # Query for summary counts per task_type
        # Summary shows all statuses, but respects task_type filter if provided
        # (status and since filters don't affect summary - it shows overall counts)
        summary_conditions: List[str] = []
        summary_params: List[Any] = []
        if task_type_val:
            summary_conditions.append("task_type = $1")
            summary_params.append(task_type_val)

        summary_where = " AND ".join(summary_conditions) if summary_conditions else "1=1"
        summary_sql = f"""
            SELECT
                task_type,
                COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'PENDING'), 0)::int AS pending,
                COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'PROCESSING'), 0)::int AS processing,
                COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'COMPLETED'), 0)::int AS completed,
                COALESCE(COUNT(*) FILTER (WHERE UPPER(status) = 'FAILED'), 0)::int AS failed
            FROM tasks
            WHERE {summary_where}
            GROUP BY task_type
            ORDER BY task_type
        """

        summary_rows = await fetch(summary_sql, *summary_params)

        # Build summary dict
        summary_dict: Dict[str, TaskSummary] = {}
        for row in summary_rows:
            task_type_key = row["task_type"]
            summary_dict[task_type_key] = TaskSummary(
                pending=int(row.get("pending") or 0),
                processing=int(row.get("processing") or 0),
                completed=int(row.get("completed") or 0),
                failed=int(row.get("failed") or 0),
            )

        # Query for total count
        count_sql = f"SELECT COUNT(*)::int AS total FROM tasks WHERE {where_sql}"
        count_rows = await fetch(count_sql, *filter_params)
        total = int(count_rows[0]["total"]) if count_rows else 0

        # Query for paginated items
        limit_placeholder = len(filter_params) + 1
        offset_placeholder = len(filter_params) + 2
        items_sql = f"""
            SELECT
                id,
                task_type,
                status,
                created_at,
                last_attempted_at,
                location_id,
                COALESCE(attempts, 0)::int AS attempts,
                payload
            FROM tasks
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${limit_placeholder} OFFSET ${offset_placeholder}
        """
        items_params = filter_params + [limit, offset]
        items_rows = await fetch(items_sql, *items_params)

        # Build items list
        items = []
        for row in items_rows:
            items.append(
                TaskItem(
                    id=int(row["id"]),
                    task_type=str(row["task_type"]),
                    status=str(row["status"]),
                    created_at=row["created_at"],
                    last_attempted_at=row.get("last_attempted_at"),
                    location_id=int(row["location_id"]) if row.get("location_id") else None,
                    attempts=int(row.get("attempts") or 0),
                    payload=row.get("payload"),
                )
            )

        return TasksResponse(
            summary=summary_dict,
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("list_tasks_endpoint_failed", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch tasks. Please try again later.",
        ) from exc


from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.models.news_pages_raw import (
    NEWS_PAGE_PROCESSING_STATES,
    NewsPageRaw,
    NewsPageRawCreate,
)
from services.db_service import execute, fetch, fetchrow

logger = get_logger()


@dataclass
class NewsPageRawRecord:
    """Internal record representation for database operations."""

    id: int
    news_source_key: str
    page_url: str
    http_status: Optional[int]
    response_headers: Dict[str, Any]
    response_body: str
    content_hash: str
    processing_state: str
    processing_errors: Optional[Dict[str, Any]]
    fetched_at: datetime
    created_at: datetime

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "NewsPageRawRecord":
        """Create NewsPageRawRecord from database row."""
        headers = row.get("response_headers") or {}
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except ValueError:
                headers = {}
        errors = row.get("processing_errors") or None
        if isinstance(errors, str):
            try:
                errors = json.loads(errors)
            except ValueError:
                errors = None
        return cls(
            id=int(row["id"]),
            news_source_key=str(row["news_source_key"]),
            page_url=str(row["page_url"]),
            http_status=row.get("http_status"),
            response_headers=headers if isinstance(headers, dict) else {},
            response_body=str(row["response_body"]),
            content_hash=str(row["content_hash"]),
            processing_state=str(row["processing_state"]),
            processing_errors=errors if isinstance(errors, dict) else None,
            fetched_at=row["fetched_at"],
            created_at=row["created_at"],
        )

    def to_model(self) -> NewsPageRaw:
        """Convert to Pydantic model."""
        return NewsPageRaw(
            id=self.id,
            news_source_key=self.news_source_key,
            page_url=self.page_url,
            http_status=self.http_status,
            response_headers=self.response_headers,
            response_body=self.response_body,
            content_hash=self.content_hash,
            processing_state=self.processing_state,
            processing_errors=self.processing_errors,
            fetched_at=self.fetched_at,
            created_at=self.created_at,
        )


async def insert_news_page_raw(payload: NewsPageRawCreate) -> Optional[int]:
    """
    Insert a news page raw row; returns new ID or None when deduped.
    
    Args:
        payload: NewsPageRawCreate model with page data
        
    Returns:
        Inserted row ID, or None if duplicate
    """
    headers_json = json.dumps(payload.response_headers or {}, ensure_ascii=False)
    errors_json = (
        json.dumps(payload.processing_errors, ensure_ascii=False)
        if payload.processing_errors is not None
        else None
    )
    row = await fetchrow(
        """
        INSERT INTO news_pages_raw (
            news_source_key,
            page_url,
            http_status,
            response_headers,
            response_body,
            content_hash,
            processing_state,
            processing_errors
        )
        VALUES (
            $1,$2,$3,CAST($4::text AS JSONB),$5,$6,$7,CAST($8::text AS JSONB)
        )
        ON CONFLICT (news_source_key, content_hash) DO NOTHING
        RETURNING id
        """,
        payload.news_source_key,
        payload.page_url,
        payload.http_status,
        headers_json,
        payload.response_body,
        payload.content_hash,
        payload.processing_state,
        errors_json,
    )
    if row:
        new_id = int(row["id"])
        logger.debug(
            "news_page_raw_inserted",
            news_source_key=payload.news_source_key,
            id=new_id,
        )
        return new_id
    logger.debug(
        "news_page_raw_deduplicated",
        news_source_key=payload.news_source_key,
        content_hash=payload.content_hash,
    )
    return None


async def fetch_pending_news_pages(*, limit: int = 50) -> List[NewsPageRaw]:
    """
    Fetch news pages awaiting extraction.
    
    Args:
        limit: Maximum number of pages to fetch
        
    Returns:
        List of NewsPageRaw models in pending state
    """
    rows = await fetch(
        """
        SELECT
            id,
            news_source_key,
            page_url,
            http_status,
            response_headers,
            response_body,
            content_hash,
            processing_state,
            processing_errors,
            fetched_at,
            created_at
        FROM news_pages_raw
        WHERE processing_state = 'pending'
        ORDER BY fetched_at ASC
        LIMIT $1
        """,
        max(0, int(limit)),
    )
    return [NewsPageRawRecord.from_row(dict(row)).to_model() for row in rows or []]


async def update_news_page_processing_state(
    page_id: int,
    *,
    state: str,
    errors: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Update processing_state and optional errors.
    
    Args:
        page_id: ID of the news page raw record
        state: New processing state (must be in NEWS_PAGE_PROCESSING_STATES)
        errors: Optional error details dictionary
    """
    normalized_state = state.strip().lower()
    if normalized_state not in NEWS_PAGE_PROCESSING_STATES:
        allowed = ", ".join(NEWS_PAGE_PROCESSING_STATES)
        raise ValueError(f"Invalid page state: {state}; expected one of {allowed}")
    errors_json = json.dumps(errors, ensure_ascii=False) if errors is not None else None
    await execute(
        """
        UPDATE news_pages_raw
        SET processing_state = $2,
            processing_errors = CAST($3::text AS JSONB)
        WHERE id = $1
        """,
        page_id,
        normalized_state,
        errors_json,
    )


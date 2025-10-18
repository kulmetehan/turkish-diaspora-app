# Backend/app/core/request_id.py
from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Iterator, Optional
import contextvars

_request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_run_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("run_id", default=None)

# -------- Request ID (API) ---------------------------------------------------

def set_request_id(request_id: Optional[str]) -> None:
    _request_id_ctx.set(request_id)

def get_request_id() -> Optional[str]:
    return _request_id_ctx.get()

def clear_request_id() -> None:
    _request_id_ctx.set(None)

# -------- Run ID (Workers) ---------------------------------------------------

def set_run_id(run_id: Optional[str]) -> None:
    _run_id_ctx.set(run_id)

def get_run_id() -> Optional[str]:
    return _run_id_ctx.get()

@contextmanager
def with_run_id(run_id: Optional[str] = None) -> Iterator[str]:
    """
    Gebruik in workers:
        with with_run_id():
            ... doe werk ...
    """
    previous = _run_id_ctx.get()
    rid = run_id or uuid.uuid4().hex
    _run_id_ctx.set(rid)
    try:
        yield rid
    finally:
        # restore vorige waarde (kan None zijn)
        _run_id_ctx.set(previous)

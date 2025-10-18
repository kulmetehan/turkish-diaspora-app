# Backend/app/core/logging.py
from __future__ import annotations

import logging
import sys
from typing import Any, Dict
from datetime import datetime, timezone

import structlog

# We halen request_id / run_id uit de context helpers
try:
    from app.core.request_id import get_request_id, get_run_id
except Exception:  # pragma: no cover
    # fallback voor vroege import tijdens bootstrap
    def get_request_id() -> str | None:
        return None
    def get_run_id() -> str | None:
        return None


# -------- Processors ---------------------------------------------------------

def _add_ts(_: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    # ISO 8601 UTC timestamp, kort & sorteerbaar
    event_dict.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    return event_dict

def _add_level(logger: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    # Stdlib levels → lowercase strings
    level = event_dict.get("level")
    if not level:
        # structlog stdlib wrapper plaatst level in "level" bij juiste config,
        # maar we forceren hier een fallback.
        level = getattr(logger, "level", "info")
    event_dict["level"] = str(level).lower()
    return event_dict

def _add_service(service_name: str):
    def _inner(_: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        event_dict.setdefault("service", service_name)
        return event_dict
    return _inner

def _add_request_or_run_ids(_: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    rid = get_request_id()
    if rid:
        event_dict.setdefault("request_id", rid)
    run = get_run_id()
    if run:
        event_dict.setdefault("run_id", run)
    return event_dict

# Eenvoudige PII-redactor (key-gebaseerd). Laat alleen de waarden staan die we nodig hebben.
_PII_KEYS = {
    "email", "e-mail", "phone", "telephone", "authorization",
    "auth", "token", "access_token", "refresh_token", "api_key", "apikey",
    "password", "pwd", "secret", "ssn",
}

def _pii_guard(_: Any, __: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    for k in list(event_dict.keys()):
        lk = str(k).lower()
        if lk in _PII_KEYS:
            event_dict[k] = "***redacted***"
    return event_dict


# -------- Public API ---------------------------------------------------------

_logger: structlog.BoundLogger | None = None

def configure_logging(service_name: str = "api", *, level: int = logging.INFO) -> None:
    """
    Configureer één globale structlog stack voor API & workers.
    """
    global _logger

    # Stdlib → naar stderr in JSON via structlog
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
        force=True,  # overschrijd eerdere configs
    )

    processors = [
        _add_ts,
        _add_level,
        _add_service(service_name),
        _add_request_or_run_ids,
        _pii_guard,
        structlog.processors.EventRenamer("event"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),  # veilig voor container logs
        cache_logger_on_first_use=True,
    )

    _logger = structlog.get_logger()

def get_logger() -> structlog.BoundLogger:
    global _logger
    if _logger is None:
        configure_logging("api")  # sane default
    return _logger

# Een makkelijk te importeren alias
logger = get_logger()

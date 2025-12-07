# services/ai_validation.py
from __future__ import annotations
from typing import Any, Dict
import structlog

from app.models.ai import (
    AIClassification, AIEnrichment, AIVerificationResult, ContentModerationResult,
    validate_classification, validate_enrichment, validate_verification, validate_moderation,
    AIValidationError,
)

log = structlog.get_logger(__name__)

def _log_result(kind: str, ok: bool, data: Dict[str, Any], err: Exception | None = None):
    if ok:
        log.info("ai_validation_ok", kind=kind)
    else:
        # log alleen een klein sample van de payload om ruis te beperken
        log.warning("ai_validation_fail", kind=kind, error=str(err), sample=str(data)[:500])

def validate_classification_payload(data: Dict[str, Any]) -> AIClassification:
    try:
        parsed = validate_classification(data)
        _log_result("classification", True, data)
        return parsed
    except AIValidationError as e:
        _log_result("classification", False, data, e)
        raise

def validate_enrichment_payload(data: Dict[str, Any]) -> AIEnrichment:
    try:
        parsed = validate_enrichment(data)
        _log_result("enrichment", True, data)
        return parsed
    except AIValidationError as e:
        _log_result("enrichment", False, data, e)
        raise

def validate_verification_payload(data: Dict[str, Any]) -> AIVerificationResult:
    try:
        parsed = validate_verification(data)
        _log_result("verification", True, data)
        return parsed
    except AIValidationError as e:
        _log_result("verification", False, data, e)
        raise

def validate_moderation_payload(data: Dict[str, Any]) -> ContentModerationResult:
    try:
        parsed = validate_moderation(data)
        _log_result("moderation", True, data)
        return parsed
    except AIValidationError as e:
        _log_result("moderation", False, data, e)
        raise

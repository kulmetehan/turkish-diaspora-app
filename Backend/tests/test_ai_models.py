# Backend/tests/test_ai_models.py
import pytest
from app.models.ai import (
    AIClassification, AIEnrichment, AIVerificationResult,
    validate_classification, validate_enrichment, validate_verification, AIValidationError,
    VerificationStatus
)

def test_classification_happy():
    data = {"action": "keep", "category": "bakery", "confidence_score": 0.91}
    obj = validate_classification(data)
    assert obj.action.value == "keep"
    assert obj.category.value == "bakery"
    assert obj.confidence_score == pytest.approx(0.91)

def test_classification_alias_score_clipped():
    data = {"action": "ignore", "category": "other", "score": 1.2}  # clipped
    obj = validate_classification(data)
    assert obj.confidence_score == 1.0

def test_classification_invalid_action():
    with pytest.raises(AIValidationError):
        validate_classification({"action": "nope", "category": "bakery", "confidence_score": 0.5})

def test_enrichment_url_normalization():
    e = validate_enrichment({"website": "example.com", "rating": 4.6, "user_ratings_total": 12})
    assert e.website.startswith("https://")
    assert e.url_valid is True

def test_enrichment_alias_websiteUri():
    e = validate_enrichment({"websiteUri": "http://ex.org", "rating": 5})
    assert e.website == "http://ex.org"

def test_verification_ok():
    v = validate_verification({"status": "VERIFIED", "reasons": ["good data"]})
    assert v.status == VerificationStatus.VERIFIED

def test_verification_invalid():
    with pytest.raises(AIValidationError):
        validate_verification({"status": "WRONG"})

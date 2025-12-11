# Backend/tests/unit/test_trending_algorithm.py
from __future__ import annotations

import math
import pytest

from app.workers.trending_worker import calculate_trending_score, WEIGHT_CHECK_INS, WEIGHT_REACTIONS, WEIGHT_NOTES, HALF_LIFE_HOURS


def test_trending_score_basic():
    """Test basic trending score calculation."""
    score = calculate_trending_score(
        check_ins=10,
        reactions=5,
        notes=2,
        age_hours=0,  # Fresh activity
    )
    
    expected = (
        WEIGHT_CHECK_INS * 10 +
        WEIGHT_REACTIONS * 5 +
        WEIGHT_NOTES * 2
    ) * math.exp(-0 / HALF_LIFE_HOURS)
    
    assert score == pytest.approx(expected)


def test_trending_score_decay():
    """Test that older activity has lower score due to decay."""
    fresh_score = calculate_trending_score(
        check_ins=10,
        reactions=5,
        notes=2,
        age_hours=0,
    )
    
    old_score = calculate_trending_score(
        check_ins=10,
        reactions=5,
        notes=2,
        age_hours=24,  # 24 hours old (half-life)
    )
    
    # Old score should be approximately half of fresh score
    assert old_score == pytest.approx(fresh_score * 0.5, rel=0.1)


def test_trending_score_zero_activity():
    """Test trending score with zero activity."""
    score = calculate_trending_score(
        check_ins=0,
        reactions=0,
        notes=0,
        age_hours=0,
    )
    
    assert score == 0.0


def test_trending_score_very_old():
    """Test that very old activity has very low score."""
    score = calculate_trending_score(
        check_ins=100,
        reactions=50,
        notes=20,
        age_hours=168,  # 7 days old
    )
    
    # Should be very small due to exponential decay
    assert score < 1.0


def test_trending_score_ranking_order():
    """Test that higher activity counts result in higher scores."""
    score_low = calculate_trending_score(
        check_ins=5,
        reactions=2,
        notes=1,
        age_hours=0,
    )
    
    score_high = calculate_trending_score(
        check_ins=20,
        reactions=10,
        notes=5,
        age_hours=0,
    )
    
    assert score_high > score_low












"""
Tests for category_map.normalize_category function.
"""
import pytest
from app.services.category_map import normalize_category


def test_barber_aliases():
    """Test that barber, barbershop, and kapper all normalize to 'barber'."""
    assert normalize_category("barber")["category_key"] == "barber"
    assert normalize_category("barbershop")["category_key"] == "barber"
    assert normalize_category("kapper")["category_key"] == "barber"
    assert normalize_category("KAPPER")["category_key"] == "barber"  # case insensitive
    assert normalize_category("Barber Shop")["category_key"] == "barber"  # spaces


def test_supermarket_aliases():
    """Test that bakkal variants normalize to 'supermarket'."""
    assert normalize_category("supermarket")["category_key"] == "supermarket"
    assert normalize_category("bakkal")["category_key"] == "supermarket"
    assert normalize_category("bakkal/supermarket")["category_key"] == "supermarket"
    assert normalize_category("bakkal_supermarket")["category_key"] == "supermarket"
    assert normalize_category("BAKKAL")["category_key"] == "supermarket"  # case


def test_fast_food_aliases():
    """Test that fast_food aliases normalize correctly."""
    assert normalize_category("fast_food")["category_key"] == "fast_food"
    assert normalize_category("snackbar")["category_key"] == "fast_food"
    assert normalize_category("kebab")["category_key"] == "fast_food"
    assert normalize_category("döner")["category_key"] == "fast_food"
    assert normalize_category("doner")["category_key"] == "fast_food"


def test_cafe_aliases():
    """Test that cafe aliases normalize correctly."""
    assert normalize_category("cafe")["category_key"] == "cafe"
    assert normalize_category("coffee")["category_key"] == "cafe"
    assert normalize_category("koffie")["category_key"] == "cafe"


def test_butcher_aliases():
    """Test that butcher aliases normalize correctly."""
    assert normalize_category("butcher")["category_key"] == "butcher"
    assert normalize_category("kasap")["category_key"] == "butcher"
    assert normalize_category("slager")["category_key"] == "butcher"


def test_other_categories():
    """Test other known categories."""
    assert normalize_category("bakery")["category_key"] == "bakery"
    assert normalize_category("restaurant")["category_key"] == "restaurant"
    assert normalize_category("mosque")["category_key"] == "mosque"
    assert normalize_category("travel_agency")["category_key"] == "travel_agency"


def test_case_insensitive():
    """Test that normalization is case-insensitive."""
    assert normalize_category("BAKERY")["category_key"] == "bakery"
    assert normalize_category("Restaurant")["category_key"] == "restaurant"
    assert normalize_category("SUPERMARKET")["category_key"] == "supermarket"


def test_whitespace_handling():
    """Test that extra whitespace is handled."""
    assert normalize_category("  bakery  ")["category_key"] == "bakery"
    assert normalize_category("fast food")["category_key"] == "fast_food"  # space -> underscore
    assert normalize_category("travel agency")["category_key"] == "travel_agency"


def test_unmappable_values():
    """Test that unmappable values return None for category_key."""
    result = normalize_category("unknown_category_xyz")
    assert result["category_key"] is None
    assert result["category_raw"] == "unknown_category_xyz"
    assert "category_label" in result  # Should still have a label


def test_empty_values():
    """Test that empty/None values return None for category_key."""
    result1 = normalize_category("")
    assert result1["category_key"] is None
    
    result2 = normalize_category(None)  # type: ignore
    assert result2["category_key"] is None


def test_label_presence():
    """Test that all results include a category_label."""
    result = normalize_category("bakery")
    assert "category_label" in result
    assert result["category_label"]  # Not empty
    
    result2 = normalize_category("unknown")
    assert "category_label" in result2
    assert result2["category_label"]  # Even unmappable has a label


def test_category_raw_preserved():
    """Test that original input is preserved in category_raw."""
    result = normalize_category("  BAKERY  ")
    assert result["category_raw"] == "  BAKERY  "
    assert result["category_key"] == "bakery"  # But key is normalized


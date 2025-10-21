#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSM Mapping Validator — Validate categories.yml osm_tags configuration
- Ensures every category has osm_tags
- Validates osm_tags structure (any/all with non-empty dicts)
- Reports validation results with clear error messages
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml


def find_categories_yml() -> Path:
    """Find the categories.yml file in the project."""
    # Try multiple possible locations
    possible_paths = [
        Path("Infra/config/categories.yml"),
        Path("../Infra/config/categories.yml"),
        Path("../../Infra/config/categories.yml"),
        Path("/Users/metehankul/Desktop/TurkishProject/Turkish Diaspora App/Infra/config/categories.yml"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    raise FileNotFoundError(
        "categories.yml not found. Tried:\n" + 
        "\n".join(f"  - {p}" for p in possible_paths)
    )


def load_categories_config() -> Dict[str, Any]:
    """Load and parse categories.yml."""
    yml_path = find_categories_yml()
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse {yml_path}: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("categories.yml root must be a dictionary")
    
    if "categories" not in data:
        raise ValueError("categories.yml must contain 'categories' key")
    
    return data


def validate_osm_tags(osm_tags: Any, category_name: str) -> List[str]:
    """Validate osm_tags structure for a category."""
    errors = []
    
    if not isinstance(osm_tags, dict):
        errors.append(f"Category '{category_name}': osm_tags must be a dictionary")
        return errors
    
    if not osm_tags:
        errors.append(f"Category '{category_name}': osm_tags cannot be empty")
        return errors
    
    # Check for required keys (any or all)
    has_any = "any" in osm_tags
    has_all = "all" in osm_tags
    
    if not has_any and not has_all:
        errors.append(f"Category '{category_name}': osm_tags must contain 'any' or 'all' key")
        return errors
    
    if has_any and has_all:
        errors.append(f"Category '{category_name}': osm_tags cannot have both 'any' and 'all' keys")
        return errors
    
    # Validate 'any' structure
    if has_any:
        any_tags = osm_tags["any"]
        if not isinstance(any_tags, list):
            errors.append(f"Category '{category_name}': osm_tags.any must be a list")
        elif not any_tags:
            errors.append(f"Category '{category_name}': osm_tags.any cannot be empty")
        else:
            for i, tag in enumerate(any_tags):
                if not isinstance(tag, dict):
                    errors.append(f"Category '{category_name}': osm_tags.any[{i}] must be a dictionary")
                elif not tag:
                    errors.append(f"Category '{category_name}': osm_tags.any[{i}] cannot be empty")
                else:
                    # Check for valid key-value pairs
                    for key, value in tag.items():
                        if not isinstance(key, str) or not key.strip():
                            errors.append(f"Category '{category_name}': osm_tags.any[{i}] has invalid key")
                        if not isinstance(value, str) or not value.strip():
                            errors.append(f"Category '{category_name}': osm_tags.any[{i}].{key} has invalid value")
    
    # Validate 'all' structure
    if has_all:
        all_tags = osm_tags["all"]
        if not isinstance(all_tags, list):
            errors.append(f"Category '{category_name}': osm_tags.all must be a list")
        elif not all_tags:
            errors.append(f"Category '{category_name}': osm_tags.all cannot be empty")
        else:
            for i, tag in enumerate(all_tags):
                if not isinstance(tag, dict):
                    errors.append(f"Category '{category_name}': osm_tags.all[{i}] must be a dictionary")
                elif not tag:
                    errors.append(f"Category '{category_name}': osm_tags.all[{i}] cannot be empty")
                else:
                    # Check for valid key-value pairs
                    for key, value in tag.items():
                        if not isinstance(key, str) or not key.strip():
                            errors.append(f"Category '{category_name}': osm_tags.all[{i}] has invalid key")
                        if not isinstance(value, str) or not value.strip():
                            errors.append(f"Category '{category_name}': osm_tags.all[{i}].{key} has invalid value")
    
    return errors


def validate_categories() -> bool:
    """Validate all categories in categories.yml."""
    print("🔍 Validating OSM mapping in categories.yml...")
    
    try:
        data = load_categories_config()
    except Exception as e:
        print(f"❌ Failed to load categories.yml: {e}")
        return False
    
    categories = data.get("categories", {})
    if not categories:
        print("❌ No categories found in categories.yml")
        return False
    
    all_errors = []
    categories_with_osm_tags = 0
    
    for category_name, category_data in categories.items():
        if not isinstance(category_data, dict):
            all_errors.append(f"Category '{category_name}': must be a dictionary")
            continue
        
        if "osm_tags" not in category_data:
            all_errors.append(f"Category '{category_name}': missing osm_tags")
            continue
        
        categories_with_osm_tags += 1
        errors = validate_osm_tags(category_data["osm_tags"], category_name)
        all_errors.extend(errors)
    
    # Report results
    print(f"\n📊 Validation Results:")
    print(f"  Total categories: {len(categories)}")
    print(f"  Categories with osm_tags: {categories_with_osm_tags}")
    print(f"  Validation errors: {len(all_errors)}")
    
    if all_errors:
        print(f"\n❌ Validation failed with {len(all_errors)} errors:")
        for error in all_errors:
            print(f"  • {error}")
        return False
    else:
        print(f"\n✅ All categories have valid osm_tags configuration!")
        return True


def main():
    """Main validation function."""
    try:
        success = validate_categories()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

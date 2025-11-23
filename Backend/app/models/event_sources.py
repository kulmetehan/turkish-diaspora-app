from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

EVENT_SOURCE_STATUSES = ("active", "disabled")
EVENT_SELECTOR_FORMATS = ("html", "rss", "json", "json_ld")


def _clean_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} cannot be empty")
    return trimmed


def sanitize_event_selectors(raw_value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize selector configuration for HTML/RSS/JSON sources while maintaining backward compatibility.
    """
    if raw_value is None:
        raw_value = {}
    if not isinstance(raw_value, dict):
        raise ValueError("selectors must be a JSON object/dict")

    normalized: Dict[str, Any] = dict(raw_value)
    fmt = str(normalized.get("format") or "html").strip().lower()
    if fmt not in EVENT_SELECTOR_FORMATS:
        raise ValueError(f"selectors.format must be one of: {', '.join(EVENT_SELECTOR_FORMATS)}")
    normalized["format"] = fmt

    if fmt == "html":
        item_selector = normalized.get("item_selector") or normalized.get("list")
        title_selector = normalized.get("title_selector") or normalized.get("title")
        if not item_selector:
            raise ValueError("selectors.item_selector (or list) is required for html format")
        if not title_selector:
            raise ValueError("selectors.title_selector (or title) is required for html format")
        normalized["item_selector"] = _clean_string(item_selector, "selectors.item_selector")
        normalized["title_selector"] = _clean_string(title_selector, "selectors.title_selector")

        url_selector = (
            normalized.get("url_selector")
            or normalized.get("link_selector")
            or normalized.get("link")
        )
        if url_selector:
            normalized["url_selector"] = _clean_string(url_selector, "selectors.url_selector")

        date_selector = normalized.get("date_selector") or normalized.get("date")
        if date_selector:
            normalized["date_selector"] = _clean_string(date_selector, "selectors.date_selector")
    elif fmt == "rss":
        item_path = normalized.get("item_path") or "entries"
        title_path = normalized.get("title_path") or "title"
        normalized["item_path"] = _clean_string(item_path, "selectors.item_path")
        normalized["title_path"] = _clean_string(title_path, "selectors.title_path")
    elif fmt == "json":
        items_path = normalized.get("items_path")
        if not items_path:
            raise ValueError("selectors.items_path is required for json format")
        normalized["items_path"] = _clean_string(items_path, "selectors.items_path")
        title_key = normalized.get("title_key") or "title"
        normalized["title_key"] = _clean_string(title_key, "selectors.title_key")
    else:  # json_ld
        items_path = normalized.get("json_items_path") or "$"
        normalized["json_items_path"] = _clean_string(items_path, "selectors.json_items_path")
        type_filter = normalized.get("json_type_filter") or "Event"
        normalized["json_type_filter"] = _clean_string(type_filter, "selectors.json_type_filter")

        script_selector = normalized.get("script_selector")
        if script_selector:
            normalized["script_selector"] = _clean_string(script_selector, "selectors.script_selector")

        for key, fallback in (
            ("json_title_field", "name"),
            ("json_url_field", "url"),
            ("json_start_field", "startDate"),
            ("json_end_field", "endDate"),
            ("json_location_field", "location.name"),
            ("json_image_field", "image"),
            ("json_description_field", "description"),
        ):
            value = normalized.get(key) or fallback
            normalized[key] = _clean_string(value, f"selectors.{key}")

    for optional_key in (
        "time_selector",
        "description_selector",
        "location_selector",
        "image_selector",
    ):
        value = normalized.get(optional_key)
        if value:
            normalized[optional_key] = _clean_string(value, f"selectors.{optional_key}")

    timezone_hint = normalized.get("timezone")
    if timezone_hint:
        normalized["timezone"] = _clean_string(timezone_hint, "selectors.timezone")

    datetime_format = normalized.get("datetime_format")
    if datetime_format:
        normalized["datetime_format"] = _clean_string(datetime_format, "selectors.datetime_format")

    locale_hint = normalized.get("locale")
    if locale_hint:
        normalized["locale"] = _clean_string(locale_hint, "selectors.locale")

    return normalized


class EventSourceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Stable identifier used by workers (slug).")
    name: str = Field(..., description="Human readable name shown in admin UI.")
    base_url: str = Field(..., description="Primary domain for the source.")
    list_url: Optional[str] = Field(
        default=None,
        description="Optional direct listing URL, falls back to base_url when missing.",
    )
    city_key: Optional[str] = Field(
        default=None,
        description="Optional city key reference from Infra/config/cities.yml.",
    )
    selectors: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON selectors/metadata describing how to scrape events.",
    )
    interval_minutes: int = Field(
        default=60,
        gt=0,
        description="Desired minutes between scrapes for this source.",
    )

    @field_validator("key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("key is required")
        normalized = value.strip().lower().replace(" ", "_")
        return normalized

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        if value is None:
            raise ValueError("base_url is required")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("base_url is required")
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return trimmed

    @field_validator("list_url")
    @classmethod
    def _validate_list_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("list_url must start with http:// or https://")
        return trimmed

    @field_validator("city_key")
    @classmethod
    def _normalize_city_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "_")
        return normalized or None

    @field_validator("selectors")
    @classmethod
    def _normalize_selectors(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        return sanitize_event_selectors(value)


class EventSourceCreate(EventSourceBase):
    status: Optional[str] = Field(
        default="active", description="Initial status for the source."
    )

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = value.strip().lower()
        if lowered not in EVENT_SOURCE_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(EVENT_SOURCE_STATUSES)}")
        return lowered


class EventSourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Optional[str] = None
    name: Optional[str] = None
    base_url: Optional[str] = None
    list_url: Optional[str] = None
    city_key: Optional[str] = None
    selectors: Optional[Dict[str, Any]] = None
    interval_minutes: Optional[int] = None
    status: Optional[str] = None

    @field_validator("key")
    @classmethod
    def _normalize_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValueError("key cannot be empty")
        return normalized

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return trimmed

    @field_validator("list_url")
    @classmethod
    def _validate_list_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("list_url must start with http:// or https://")
        return trimmed

    @field_validator("selectors")
    @classmethod
    def _normalize_selectors(cls, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        return sanitize_event_selectors(value)

    @field_validator("city_key")
    @classmethod
    def _normalize_city_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "_")
        return normalized or None

    @field_validator("interval_minutes")
    @classmethod
    def _validate_interval(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        ivalue = int(value)
        if ivalue <= 0:
            raise ValueError("interval_minutes must be > 0")
        return ivalue

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        lowered = value.strip().lower()
        if lowered not in EVENT_SOURCE_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(EVENT_SOURCE_STATUSES)}")
        return lowered


class EventSource(EventSourceBase):
    id: int
    status: str
    last_run_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime



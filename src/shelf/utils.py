"""Pure helpers for fragrance shelf logic."""

from __future__ import annotations

from typing import Any


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _lower_or_empty(value: Any) -> str:
    return _normalize_text(value).lower()


def _dict_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_sex(value: Any) -> str:
    raw = _lower_or_empty(value)
    if raw in {"women", "woman", "female", "f"}:
        return "woman"
    if raw in {"men", "man", "male", "m"}:
        return "men"
    if raw in {"unisex", "u"}:
        return "unisex"
    return raw


def _format_sex_label(value: Any) -> str:
    normalized = _normalize_sex(value)
    if normalized == "woman":
        return "Women"
    if normalized == "men":
        return "Men"
    if normalized == "unisex":
        return "Unisex"
    return _normalize_text(value)


def _item_key(brand: Any, name: Any, fragrance_id: Any = None) -> str:
    fid = _normalize_text(fragrance_id)
    if fid:
        return f"id::{fid.lower()}"
    return f"name::{_lower_or_empty(brand)}::{_lower_or_empty(name)}"

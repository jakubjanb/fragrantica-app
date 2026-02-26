"""Database access layer for shelf and recommendation log tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.shelf.auth import get_supabase_client
from src.shelf.constants import ENABLE_RECOMMENDATION_LOG
from src.shelf.utils import _normalize_text


def fetch_user_shelf(user_id: str) -> pd.DataFrame:
    sb = get_supabase_client()
    response = (
        sb.table("user_shelf")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = response.data or []
    df = pd.DataFrame(rows)

    expected_cols = [
        "id",
        "user_id",
        "fragrance_id",
        "brand",
        "name",
        "user_rating",
        "created_at",
        "updated_at",
    ]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df["brand"] = df["brand"].fillna("").astype(str).str.strip()
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["fragrance_id"] = df["fragrance_id"].apply(lambda x: _normalize_text(x) or None)
    df["user_rating"] = pd.to_numeric(df["user_rating"], errors="coerce")
    return df[expected_cols].copy()


def add_to_shelf(user_id: str, item: dict[str, Any], rating: int | None) -> tuple[bool, str]:
    sb = get_supabase_client()
    brand = _normalize_text(item.get("brand"))
    name = _normalize_text(item.get("name"))
    fragrance_id = _normalize_text(item.get("fragrance_id")) or None

    if not brand or not name:
        return False, "Selected catalog row does not contain valid brand/name fields."

    payload = {
        "user_id": user_id,
        "brand": brand,
        "name": name,
        "fragrance_id": fragrance_id,
        "user_rating": int(rating) if rating is not None else None,
    }

    try:
        sb.table("user_shelf").insert(payload).execute()
        return True, "Fragrance added to your shelf."
    except Exception as exc:
        err = str(exc).lower()
        if "duplicate" in err or "unique" in err:
            return False, "This fragrance is already on your shelf."
        return False, f"Could not add fragrance: {exc}"


def update_shelf_rating(row_id: str, rating: int | None) -> tuple[bool, str]:
    sb = get_supabase_client()
    payload = {"user_rating": int(rating) if rating is not None else None}
    try:
        sb.table("user_shelf").update(payload).eq("id", row_id).execute()
        return True, "Rating saved."
    except Exception as exc:
        return False, f"Could not update rating: {exc}"


def delete_shelf_item(row_id: str) -> tuple[bool, str]:
    sb = get_supabase_client()
    try:
        sb.table("user_shelf").delete().eq("id", row_id).execute()
        return True, "Fragrance removed from shelf."
    except Exception as exc:
        return False, f"Could not remove fragrance: {exc}"


def _log_recommendations(user_id: str, df_recs: pd.DataFrame) -> None:
    if not ENABLE_RECOMMENDATION_LOG or df_recs.empty:
        return
    if "fragrance_id" not in df_recs.columns:
        return

    records = []
    for _, row in df_recs.iterrows():
        fragrance_id = _normalize_text(row.get("fragrance_id"))
        if not fragrance_id:
            continue
        records.append(
            {
                "user_id": user_id,
                "fragrance_id": fragrance_id,
                "score": float(row.get("score", 0.0)),
            }
        )

    if not records:
        return

    sb = get_supabase_client()
    sb.table("recommendation_log").insert(records).execute()

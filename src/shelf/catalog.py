"""Catalog loading and normalization for shelf workflows."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.shelf.utils import _item_key, _normalize_sex, _normalize_text


@st.cache_data(show_spinner=False)
def load_catalog_df() -> pd.DataFrame:
    df: pd.DataFrame | None = None

    # TODO: align with src.data.py if a dedicated catalog loader is introduced.
    try:
        from src.data import load_fragrances  # type: ignore

        df = load_fragrances()
    except Exception:
        pass

    if df is None:
        try:
            from src.data import get_fragrances_df  # type: ignore

            df = get_fragrances_df()
        except Exception:
            pass

    if df is None:
        try:
            from src import data as data_module  # type: ignore

            if hasattr(data_module, "fragrances"):
                maybe_df = getattr(data_module, "fragrances")
                if isinstance(maybe_df, pd.DataFrame):
                    df = maybe_df.copy()
        except Exception:
            pass

    if df is None:
        from src.data import load_data

        dataset_path = os.getenv("DATASET_CSV_PATH", "Data/all_brands_clean.csv")
        csv_path = Path(dataset_path)
        if not csv_path.is_absolute():
            csv_path = (Path(__file__).resolve().parents[2] / csv_path).resolve()
        df = load_data(csv_path)

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "brand",
                "name",
                "fragrance_id",
                "fragrance_category",
                "sex",
                "rating",
                "votes",
                "catalog_key",
                "display_label",
            ]
        )

    df = df.copy()

    alias_map = {
        "fragrance_category": ["category", "fragrance_family", "family"],
        "sex": ["gender", "target"],
        "fragrance_id": ["id", "perfume_id", "fragrantica_id"],
    }
    for target_col, aliases in alias_map.items():
        if target_col not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    df[target_col] = df[alias]
                    break

    for required in ("brand", "name"):
        if required not in df.columns:
            raise RuntimeError(
                f"Required column '{required}' is missing in the fragrance catalog."
            )

    if "fragrance_category" not in df.columns:
        df["fragrance_category"] = ""
    if "sex" not in df.columns:
        df["sex"] = ""
    if "fragrance_id" not in df.columns:
        df["fragrance_id"] = pd.NA
    if "rating" not in df.columns:
        df["rating"] = np.nan
    if "votes" not in df.columns:
        df["votes"] = np.nan

    df["brand"] = df["brand"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["fragrance_category"] = df["fragrance_category"].fillna("").astype(str).str.strip()
    df["sex"] = df["sex"].fillna("").astype(str).str.strip().str.lower().map(_normalize_sex)
    df["fragrance_id"] = (
        df["fragrance_id"]
        .where(df["fragrance_id"].notna(), None)
        .apply(lambda x: _normalize_text(x) or None)
    )
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce")

    df = df[(df["brand"] != "") & (df["name"] != "")].copy()
    df["catalog_key"] = df.apply(
        lambda row: _item_key(row["brand"], row["name"], row.get("fragrance_id")), axis=1
    )
    df["display_label"] = df["brand"] + " — " + df["name"]
    df = df.drop_duplicates(subset=["catalog_key"]).reset_index(drop=True)
    return df

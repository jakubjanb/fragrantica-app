from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_data(csv_path: Path | str) -> pd.DataFrame:
    """
    Load and clean the perfume dataset.

    - Ensures numeric types for rating and votes
    - Drops rows missing essential fields
    - Casts url to string when present
    """
    path = Path(csv_path)
    df = pd.read_csv(path)

    # Coerce numeric columns
    for col in ("rating", "votes"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep essential columns
    essential = [c for c in ["brand", "name", "rating", "votes"] if c in df.columns]
    if not set(["brand", "name", "rating", "votes"]).issubset(df.columns):
        # If any are missing, return empty to let the app report nicely
        return pd.DataFrame(columns=["brand", "name", "rating", "votes"])  # type: ignore[return-value]

    df = df.dropna(subset=["brand", "name", "rating", "votes"]).copy()

    if "url" in df.columns:
        df["url"] = df["url"].astype(str)

    return df


def list_brands(df: pd.DataFrame) -> List[str]:
    if "brand" not in df.columns or df.empty:
        return []
    brands = sorted(df["brand"].dropna().astype(str).unique().tolist())
    return brands

"""Candidate generation for hybrid recommendations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from src.shelf.recommender.artifacts import RecommenderArtifacts
from src.shelf.utils import _item_key


def _normalize_user_scores(df_shelf: pd.DataFrame) -> pd.Series:
    ratings = pd.to_numeric(df_shelf.get("user_rating"), errors="coerce")
    if ratings.notna().any():
        filled = ratings.fillna(float(ratings.median()))
    else:
        filled = pd.Series(np.full(len(df_shelf), 7.0), index=df_shelf.index, dtype="float64")
    clipped = filled.clip(lower=1.0, upper=10.0)
    return (clipped / 10.0).astype(float)


def build_category_affinity(df_shelf: pd.DataFrame) -> dict[str, float]:
    if df_shelf.empty:
        return {}

    shelf = df_shelf.copy()
    if "fragrance_category" not in shelf.columns:
        shelf["fragrance_category"] = ""

    shelf["fragrance_category"] = shelf["fragrance_category"].fillna("").astype(str).str.strip()
    shelf = shelf[shelf["fragrance_category"] != ""].copy()
    if shelf.empty:
        return {}

    shelf["score_weight"] = _normalize_user_scores(shelf)
    denom = float(shelf["score_weight"].sum())
    if denom <= 1e-12:
        return {}

    pref = shelf.groupby("fragrance_category", dropna=False)["score_weight"].sum() / denom
    return {str(cat): float(val) for cat, val in pref.to_dict().items()}


def _catalog_key_series(df: pd.DataFrame) -> pd.Series:
    if "catalog_key" in df.columns:
        return df["catalog_key"].astype(str)
    return df.apply(
        lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
        axis=1,
    )


def generate_candidates(
    catalog: pd.DataFrame,
    shelf: pd.DataFrame,
    artifacts: RecommenderArtifacts,
    *,
    min_seed_rating: int = 7,
    neighbor_k: int = 80,
    per_category_k: int = 80,
    global_k: int = 250,
) -> pd.DataFrame:
    """
    Build a deduplicated candidate set from CF neighbors + category + global priors.
    """
    if catalog.empty:
        return pd.DataFrame()

    cdf = catalog.copy()
    cdf["catalog_key"] = _catalog_key_series(cdf)
    if "fragrance_category" not in cdf.columns:
        cdf["fragrance_category"] = ""
    if "quality_score" not in cdf.columns:
        cdf["quality_score"] = 0.0
    cdf["fragrance_category"] = cdf["fragrance_category"].fillna("").astype(str).str.strip()
    cdf["quality_score"] = pd.to_numeric(cdf["quality_score"], errors="coerce").fillna(0.0)

    shelf_df = shelf.copy() if shelf is not None else pd.DataFrame()
    if shelf_df.empty:
        shelf_df["catalog_key"] = pd.Series(dtype="object")
        shelf_df["user_rating"] = pd.Series(dtype="float64")
    else:
        shelf_df["catalog_key"] = _catalog_key_series(shelf_df)

    owned_keys: set[str] = set(shelf_df["catalog_key"].dropna().astype(str).tolist())

    cdf["item_idx"] = cdf["catalog_key"].map(artifacts.item_index)

    cf_scores: dict[int, float] = defaultdict(float)
    cf_weight_sum = 0.0

    seed_df = shelf_df.copy()
    seed_df["user_rating"] = pd.to_numeric(seed_df.get("user_rating"), errors="coerce")
    rated_seed_df = seed_df[seed_df["user_rating"].notna()].copy()
    seed_min = float(min_seed_rating)
    rated_seed_df = rated_seed_df[rated_seed_df["user_rating"] >= seed_min]

    if rated_seed_df.empty and not seed_df.empty:
        # Sparse shelves often have unrated entries; fall back to all known items.
        rated_seed_df = seed_df.copy()
        rated_seed_df["user_rating"] = pd.to_numeric(rated_seed_df["user_rating"], errors="coerce").fillna(7.0)

    if not rated_seed_df.empty:
        rated_seed_df["seed_weight"] = _normalize_user_scores(rated_seed_df)

        for row in rated_seed_df.itertuples(index=False):
            seed_key = str(getattr(row, "catalog_key", "") or "")
            if not seed_key:
                continue
            seed_idx = artifacts.item_index.get(seed_key)
            if seed_idx is None:
                continue
            seed_weight = float(getattr(row, "seed_weight", 0.0) or 0.0)
            if seed_weight <= 0.0:
                continue

            neighbors = artifacts.neighbors_by_item.get(seed_idx, [])
            for neighbor_idx, sim in neighbors[:neighbor_k]:
                cf_scores[int(neighbor_idx)] += seed_weight * float(sim)
            cf_weight_sum += seed_weight

    if cf_weight_sum > 1e-12:
        for idx in list(cf_scores.keys()):
            cf_scores[idx] = float(cf_scores[idx] / cf_weight_sum)

    category_pref = build_category_affinity(shelf_df)

    candidate_keys: set[str] = set()

    if cf_scores:
        for idx in cf_scores:
            key = artifacts.index_to_key.get(int(idx))
            if key:
                candidate_keys.add(key)

    if category_pref:
        categories_ranked = sorted(category_pref.items(), key=lambda it: it[1], reverse=True)
        for cat, _ in categories_ranked[:4]:
            in_cat = cdf[cdf["fragrance_category"] == str(cat)]
            top_cat = in_cat.sort_values("quality_score", ascending=False).head(per_category_k)
            candidate_keys.update(top_cat["catalog_key"].astype(str).tolist())

    top_global = cdf.sort_values("quality_score", ascending=False).head(global_k)
    candidate_keys.update(top_global["catalog_key"].astype(str).tolist())

    candidate_keys.difference_update(owned_keys)

    if not candidate_keys:
        return pd.DataFrame()

    out = cdf[cdf["catalog_key"].isin(candidate_keys)].copy()
    out = out.drop_duplicates(subset=["catalog_key"]).reset_index(drop=True)

    out["cf_score"] = out["item_idx"].map(lambda i: float(cf_scores.get(int(i), 0.0)) if pd.notna(i) else 0.0)
    out["cat_affinity"] = out["fragrance_category"].map(
        lambda cat: float(category_pref.get(str(cat), 0.0))
    )
    out["cat_affinity"] = pd.to_numeric(out["cat_affinity"], errors="coerce").fillna(0.0).clip(lower=0.0)

    return out

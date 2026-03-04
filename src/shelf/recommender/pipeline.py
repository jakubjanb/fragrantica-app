"""Hybrid recommendation pipeline orchestration."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.shelf.constants import (
    FAMILY_KEYWORDS,
    FAMILY_ORDER,
    RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA,
    RECOMMENDER_DEBUG_DEFAULT,
    RECOMMENDER_GLOBAL_K,
    RECOMMENDER_MIN_SEED_RATING,
    RECOMMENDER_NEIGHBOR_K,
    RECOMMENDER_TOP_CATEGORY_K,
)
from src.shelf.recommender.artifacts import (
    artifacts_available,
    get_recommender_model_meta,
    load_recommender_artifacts,
)
from src.shelf.recommender.candidates import generate_candidates
from src.shelf.recommender.mmr import rerank_mmr
from src.shelf.recommender.quality import compute_bayesian_quality
from src.shelf.recommender.ranker import rank_candidates
from src.shelf.utils import _item_key, _lower_or_empty, _normalize_sex

_RUNTIME_OPTIONS: dict[str, Any] = {
    "debug": bool(RECOMMENDER_DEBUG_DEFAULT),
    "mmr_lambda": float(RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA),
}


def set_runtime_options(*, debug: bool | None = None, mmr_lambda: float | None = None) -> None:
    """Set per-session runtime options used without changing recommend() signature."""
    if debug is not None:
        _RUNTIME_OPTIONS["debug"] = bool(debug)
    if mmr_lambda is not None:
        _RUNTIME_OPTIONS["mmr_lambda"] = float(max(0.0, min(1.0, mmr_lambda)))


def get_runtime_options() -> dict[str, Any]:
    return dict(_RUNTIME_OPTIONS)


def _compute_family(category: Any) -> str:
    text = _lower_or_empty(category)
    if not text:
        return "Other"

    for family in FAMILY_ORDER:
        if family.lower() != "other" and text.startswith(family.lower()):
            return family

    for family, keywords in FAMILY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return family

    return "Other"


def _resolve_preferred_sex(user_pref_sex: str, shelf: pd.DataFrame) -> str:
    pref = _normalize_sex(user_pref_sex)
    if pref in {"", "auto"}:
        if shelf.empty or "sex" not in shelf.columns:
            return ""
        shelf_sex = shelf["sex"].fillna("").apply(_normalize_sex)
        counts = shelf_sex[shelf_sex != ""].value_counts()
        if counts.empty:
            return ""
        return str(counts.index[0])
    return pref


def _score_sex(candidate_sex: str, preference: str) -> float:
    if not preference or preference == "any":
        return 0.5
    if not candidate_sex:
        return 0.4
    if candidate_sex == preference:
        return 1.0
    if candidate_sex == "unisex" and preference in {"woman", "men"}:
        return 0.85
    if preference == "unisex" and candidate_sex in {"woman", "men"}:
        return 0.75
    return 0.0


def recommend_hybrid(
    df_catalog: pd.DataFrame,
    df_shelf: pd.DataFrame,
    user_pref_sex: str,
    top_n: int = 10,
    *,
    debug: bool | None = None,
    diversity_lambda: float | None = None,
) -> pd.DataFrame:
    """Hybrid recommendation flow: quality prior + CF candidates + MMR reranking."""
    if df_catalog.empty:
        return pd.DataFrame()

    artifacts = load_recommender_artifacts()
    if artifacts is None:
        return pd.DataFrame()

    opts = get_runtime_options()
    debug_mode = bool(opts.get("debug", False) if debug is None else debug)
    mmr_lambda = float(
        opts.get("mmr_lambda", RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA)
        if diversity_lambda is None
        else diversity_lambda
    )

    catalog = df_catalog.copy()
    shelf = df_shelf.copy() if df_shelf is not None else pd.DataFrame()

    for col in ("brand", "name", "fragrance_category", "sex", "rating", "votes", "fragrance_id", "url"):
        if col not in catalog.columns:
            catalog[col] = pd.NA

    if "catalog_key" not in catalog.columns:
        catalog["catalog_key"] = catalog.apply(
            lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
            axis=1,
        )

    catalog["sex"] = catalog["sex"].fillna("").apply(_normalize_sex)
    catalog["fragrance_category"] = catalog["fragrance_category"].fillna("").astype(str).str.strip()

    if not shelf.empty:
        for col in ("brand", "name", "fragrance_id", "fragrance_category", "sex", "user_rating"):
            if col not in shelf.columns:
                shelf[col] = pd.NA
        shelf["fragrance_category"] = shelf["fragrance_category"].fillna("").astype(str).str.strip()
        shelf["sex"] = shelf["sex"].fillna("").apply(_normalize_sex)

    catalog = compute_bayesian_quality(catalog)

    candidates = generate_candidates(
        catalog,
        shelf,
        artifacts,
        min_seed_rating=RECOMMENDER_MIN_SEED_RATING,
        neighbor_k=RECOMMENDER_NEIGHBOR_K,
        per_category_k=RECOMMENDER_TOP_CATEGORY_K,
        global_k=RECOMMENDER_GLOBAL_K,
    )
    if candidates.empty:
        return pd.DataFrame()

    pref_sex = _resolve_preferred_sex(user_pref_sex, shelf)
    candidates["sex"] = candidates["sex"].fillna("").apply(_normalize_sex)
    candidates["sex_score"] = candidates["sex"].apply(lambda s: _score_sex(s, pref_sex))

    ranked = rank_candidates(candidates)

    # Preserve audience preference behavior without changing core scoring formula.
    if pref_sex and pref_sex != "any":
        preferred = ranked[ranked["sex_score"] > 0.0].copy()
        non_preferred = ranked[ranked["sex_score"] <= 0.0].copy()
        if not preferred.empty:
            ranked = pd.concat([preferred, non_preferred], ignore_index=True)

    reranked = rerank_mmr(
        ranked,
        item_vectors=artifacts.item_vectors,
        item_index=artifacts.item_index,
        top_n=top_n,
        lambda_=mmr_lambda,
    )
    if reranked.empty:
        return pd.DataFrame()

    reranked["family"] = reranked["fragrance_category"].apply(_compute_family)

    preferred_cols = [
        "brand",
        "name",
        "sex",
        "fragrance_category",
        "rating",
        "votes",
        "family",
        "score",
        "fragrance_id",
        "url",
    ]

    if debug_mode:
        preferred_cols.extend(
            [
                "catalog_key",
                "cf_score",
                "cf_norm",
                "cat_affinity",
                "cat_norm",
                "quality_score",
                "quality_norm",
                "cf_component",
                "cat_component",
                "quality_component",
                "sex_score",
                "bayesian_rating",
                "quality_prior",
            ]
        )

    existing_cols = [col for col in preferred_cols if col in reranked.columns]
    return reranked[existing_cols].copy().reset_index(drop=True)


__all__ = [
    "artifacts_available",
    "get_recommender_model_meta",
    "recommend_hybrid",
    "set_runtime_options",
]

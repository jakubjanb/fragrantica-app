"""Evaluate Recommender V2 with leave-one-out metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shelf.catalog import load_catalog_df
from src.shelf.recommender.artifacts import artifacts_available, load_recommender_artifacts
from src.shelf.recommender.pipeline import recommend_hybrid
from src.shelf.utils import _item_key, _normalize_text

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*args: object, **kwargs: object) -> bool:
        return False

try:
    from supabase import create_client
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Missing package 'supabase'. Install with: pip install supabase") from exc


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")


def _get_supabase_client():
    _load_env()
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in env/.env.")
    return create_client(url, service_key)


def _fetch_all_user_shelf(batch_size: int = 1000) -> pd.DataFrame:
    sb = _get_supabase_client()
    offset = 0
    rows: list[dict[str, Any]] = []

    while True:
        response = (
            sb.table("user_shelf")
            .select("user_id,fragrance_id,brand,name,user_rating,created_at")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["user_id", "fragrance_id", "brand", "name", "user_rating", "created_at"])

    for col in ("user_id", "fragrance_id", "brand", "name", "user_rating", "created_at"):
        if col not in df.columns:
            df[col] = pd.NA

    df["user_id"] = df["user_id"].fillna("").astype(str).str.strip()
    df["brand"] = df["brand"].fillna("").astype(str).str.strip()
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["fragrance_id"] = df["fragrance_id"].apply(lambda x: _normalize_text(x) or None)
    df["user_rating"] = pd.to_numeric(df["user_rating"], errors="coerce")
    return df[df["user_id"] != ""].copy()


def _prepare_catalog() -> pd.DataFrame:
    catalog = load_catalog_df().copy()
    if catalog.empty:
        raise RuntimeError("Catalog is empty; cannot evaluate recommender.")
    if "catalog_key" not in catalog.columns:
        catalog["catalog_key"] = catalog.apply(
            lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
            axis=1,
        )
    return catalog.drop_duplicates(subset=["catalog_key"]).reset_index(drop=True)


def _prepare_interactions(df_shelf: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    if df_shelf.empty:
        return pd.DataFrame()

    df = df_shelf.copy()
    df["catalog_key"] = df.apply(
        lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
        axis=1,
    )

    valid_keys = set(catalog["catalog_key"].astype(str).tolist())
    df = df[df["catalog_key"].isin(valid_keys)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.sort_values(["user_id", "created_at"], ascending=[True, False], kind="mergesort")
    return df.reset_index(drop=True)


def _mean_ild(rec_keys: list[str], item_vectors: np.ndarray | None, item_index: dict[str, int]) -> float | None:
    if item_vectors is None or len(rec_keys) < 2:
        return None

    idxs = [item_index.get(k) for k in rec_keys]
    idxs = [int(i) for i in idxs if i is not None and 0 <= int(i) < item_vectors.shape[0]]
    if len(idxs) < 2:
        return None

    vecs = item_vectors[idxs]
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms <= 1e-12] = 1.0
    vecs = vecs / norms

    n = len(vecs)
    dists: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(np.dot(vecs[i], vecs[j]))
            dists.append(max(0.0, min(2.0, 1.0 - sim)))
    if not dists:
        return None
    return float(np.mean(dists))


def evaluate(
    *,
    top_k: int,
    min_user_items: int,
    max_users: int,
    seed: int,
) -> dict[str, Any]:
    if not artifacts_available():
        raise RuntimeError("Artifacts are missing. Train model first: python scripts/train_recommender.py")

    artifacts = load_recommender_artifacts()
    if artifacts is None:
        raise RuntimeError("Could not load artifacts.")

    catalog = _prepare_catalog()
    raw_shelf = _fetch_all_user_shelf()
    interactions = _prepare_interactions(raw_shelf, catalog)
    if interactions.empty:
        raise RuntimeError("No interactions mapped to catalog items.")

    counts = interactions.groupby("user_id")["catalog_key"].nunique()
    eligible_users = counts[counts >= min_user_items].index.tolist()
    if not eligible_users:
        raise RuntimeError("No users with enough interactions for leave-one-out evaluation.")

    rng = np.random.default_rng(seed)
    if len(eligible_users) > max_users:
        eligible_users = rng.choice(np.array(eligible_users, dtype=object), size=max_users, replace=False).tolist()

    join_cols = [c for c in ["catalog_key", "fragrance_category", "sex"] if c in catalog.columns]
    catalog_lookup = catalog[join_cols].drop_duplicates(subset=["catalog_key"])

    total = 0
    hits = 0
    ndcg_sum = 0.0
    recommended_keys: set[str] = set()
    ild_values: list[float] = []

    for user_id in eligible_users:
        user_hist = interactions[interactions["user_id"] == user_id].copy()
        if len(user_hist) < min_user_items:
            continue

        holdout = user_hist.iloc[0]
        holdout_key = str(holdout["catalog_key"])

        observed = user_hist.iloc[1:].copy()
        if observed.empty:
            continue

        observed = observed.merge(catalog_lookup, on="catalog_key", how="left")
        recs = recommend_hybrid(
            df_catalog=catalog,
            df_shelf=observed,
            user_pref_sex="auto",
            top_n=top_k,
            debug=False,
        )
        if recs.empty:
            total += 1
            continue

        rec_keys = recs.apply(
            lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
            axis=1,
        ).tolist()

        recommended_keys.update(rec_keys)
        total += 1

        if holdout_key in rec_keys:
            rank = rec_keys.index(holdout_key) + 1
            hits += 1
            ndcg_sum += 1.0 / np.log2(rank + 1)

        ild = _mean_ild(rec_keys, artifacts.item_vectors, artifacts.item_index)
        if ild is not None:
            ild_values.append(float(ild))

    if total == 0:
        raise RuntimeError("Evaluation produced zero valid users.")

    recall_at_k = hits / total
    ndcg_at_k = ndcg_sum / total
    coverage = len(recommended_keys) / max(1, int(catalog["catalog_key"].nunique()))
    ild_mean = float(np.mean(ild_values)) if ild_values else None

    return {
        "users_evaluated": int(total),
        f"recall@{top_k}": float(recall_at_k),
        f"ndcg@{top_k}": float(ndcg_at_k),
        "catalog_coverage": float(coverage),
        "intra_list_diversity": ild_mean,
        "artifact_meta": artifacts.meta,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate recommender artifacts with leave-one-out")
    parser.add_argument("--top-k", type=int, default=10, help="K for Recall@K and NDCG@K")
    parser.add_argument("--min-user-items", type=int, default=4, help="Min shelf size per user to include")
    parser.add_argument("--max-users", type=int, default=300, help="Max number of users to evaluate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for user sampling")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = evaluate(
        top_k=max(1, int(args.top_k)),
        min_user_items=max(2, int(args.min_user_items)),
        max_users=max(1, int(args.max_users)),
        seed=int(args.seed),
    )
    print("Evaluation complete.")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

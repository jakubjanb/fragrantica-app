"""Train Recommender V2 artifacts from Supabase shelf interactions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shelf.catalog import load_catalog_df
from src.shelf.constants import RECOMMENDER_ARTIFACTS_DIR
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

    for col in ("user_id", "fragrance_id", "brand", "name", "user_rating"):
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
        raise RuntimeError("Catalog is empty; cannot train recommender.")

    if "catalog_key" not in catalog.columns:
        catalog["catalog_key"] = catalog.apply(
            lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
            axis=1,
        )

    catalog = catalog.drop_duplicates(subset=["catalog_key"]).reset_index(drop=True)
    catalog["item_idx"] = np.arange(len(catalog), dtype=int)
    return catalog


def _prepare_interactions(df_shelf: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    if df_shelf.empty:
        return pd.DataFrame(columns=["user_id", "catalog_key", "item_idx", "weight"])

    interactions = df_shelf.copy()
    interactions["catalog_key"] = interactions.apply(
        lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
        axis=1,
    )
    interactions["user_rating"] = pd.to_numeric(interactions["user_rating"], errors="coerce")
    interactions["user_rating"] = interactions["user_rating"].fillna(7.0).clip(1.0, 10.0)
    interactions["weight"] = interactions["user_rating"] / 10.0

    item_map = dict(zip(catalog["catalog_key"], catalog["item_idx"]))
    interactions["item_idx"] = interactions["catalog_key"].map(item_map)
    interactions = interactions.dropna(subset=["item_idx"]).copy()
    interactions["item_idx"] = interactions["item_idx"].astype(int)

    interactions = interactions.drop_duplicates(subset=["user_id", "catalog_key"]).reset_index(drop=True)
    return interactions[["user_id", "catalog_key", "item_idx", "weight"]].copy()


def _build_weighted_neighbors(
    interactions: pd.DataFrame,
    *,
    top_k: int,
) -> pd.DataFrame:
    co: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    item_strength: dict[int, float] = defaultdict(float)

    for _, grp in interactions.groupby("user_id", sort=False):
        if len(grp) < 2:
            continue
        g = grp[["item_idx", "weight"]].drop_duplicates(subset=["item_idx"]).copy()
        n = len(g)
        if n < 2:
            continue

        scale = 1.0 / np.log1p(float(n))
        idxs = g["item_idx"].astype(int).tolist()
        ws = g["weight"].astype(float).tolist()

        for idx, w in zip(idxs, ws):
            item_strength[idx] += (w * w) * scale

        for i in range(n):
            idx_i = idxs[i]
            w_i = ws[i]
            for j in range(i + 1, n):
                idx_j = idxs[j]
                w_j = ws[j]
                val = (w_i * w_j) * scale
                if val <= 0.0:
                    continue
                co[idx_i][idx_j] += val
                co[idx_j][idx_i] += val

    rows: list[dict[str, Any]] = []
    for item_idx, neigh in co.items():
        denom_i = float(np.sqrt(item_strength.get(item_idx, 0.0)))
        if denom_i <= 1e-12:
            continue

        sims: list[tuple[int, float]] = []
        for neigh_idx, val in neigh.items():
            denom_j = float(np.sqrt(item_strength.get(neigh_idx, 0.0)))
            if denom_j <= 1e-12:
                continue
            sim = float(val / (denom_i * denom_j))
            if np.isfinite(sim) and sim > 0:
                sims.append((int(neigh_idx), sim))

        sims.sort(key=lambda t: t[1], reverse=True)
        for rank, (neighbor_idx, sim) in enumerate(sims[:top_k], start=1):
            rows.append(
                {
                    "item_idx": int(item_idx),
                    "neighbor_idx": int(neighbor_idx),
                    "sim": float(sim),
                    "rank": int(rank),
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["item_idx", "neighbor_idx", "sim", "rank"])
    return out.sort_values(["item_idx", "rank"], ascending=[True, True]).reset_index(drop=True)


def _build_item_vectors(interactions: pd.DataFrame, n_items: int, random_state: int = 42) -> np.ndarray | None:
    if interactions.empty:
        return None

    user_ids = interactions["user_id"].astype(str).unique().tolist()
    if not user_ids:
        return None

    user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
    row = interactions["user_id"].map(user_to_idx).astype(int).to_numpy()
    col = interactions["item_idx"].astype(int).to_numpy()
    data = interactions["weight"].astype(float).to_numpy()

    n_users = len(user_to_idx)
    if n_users < 2 or n_items < 2:
        return None

    X = csr_matrix((data, (row, col)), shape=(n_users, n_items), dtype=np.float32)
    max_components = min(64, n_users - 1, n_items - 1)
    if max_components < 2:
        return None

    svd = TruncatedSVD(n_components=max_components, random_state=random_state)
    svd.fit(X)
    item_vectors = svd.components_.T
    if item_vectors.shape[0] != n_items:
        return None
    return item_vectors.astype(np.float32)


def train(
    *,
    artifact_dir: Path,
    top_k: int,
) -> dict[str, Any]:
    catalog = _prepare_catalog()
    shelf = _fetch_all_user_shelf()
    interactions = _prepare_interactions(shelf, catalog)

    if interactions.empty:
        raise RuntimeError("No interactions mapped to catalog items. Cannot build model artifacts.")

    neighbors = _build_weighted_neighbors(interactions, top_k=top_k)
    item_vectors = _build_item_vectors(interactions, n_items=len(catalog))

    artifact_dir.mkdir(parents=True, exist_ok=True)

    item_index_df = catalog[["catalog_key", "item_idx"]].copy()
    item_index_df.to_parquet(artifact_dir / "item_index.parquet", index=False)
    neighbors.to_parquet(artifact_dir / "item_neighbors.parquet", index=False)

    if item_vectors is not None:
        np.save(artifact_dir / "item_vectors.npy", item_vectors)
    elif (artifact_dir / "item_vectors.npy").exists():
        (artifact_dir / "item_vectors.npy").unlink()

    meta = {
        "model_version": "recommender_v2_itemitem_v1",
        "trained_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "algorithm": "weighted_item_item_cooccurrence + optional_truncated_svd",
        "catalog_items": int(len(catalog)),
        "users": int(interactions["user_id"].nunique()),
        "interactions": int(len(interactions)),
        "neighbors": int(len(neighbors)),
        "has_item_vectors": bool(item_vectors is not None),
        "top_k": int(top_k),
    }
    with (artifact_dir / "meta.json").open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train recommender artifacts for Fragrance Shelf")
    parser.add_argument(
        "--artifact-dir",
        type=str,
        default=RECOMMENDER_ARTIFACTS_DIR,
        help="Artifact output directory.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=120,
        help="Number of nearest neighbors saved per item.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_absolute():
        artifact_dir = (root / artifact_dir).resolve()

    meta = train(artifact_dir=artifact_dir, top_k=max(int(args.top_k), 10))
    print("Training complete.")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()

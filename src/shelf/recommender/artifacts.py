"""Loading and caching recommender model artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from src.shelf.constants import RECOMMENDER_ARTIFACTS_DIR


@dataclass(frozen=True)
class RecommenderArtifacts:
    """In-memory representation of model artifacts used at serve time."""

    item_index: dict[str, int]
    index_to_key: dict[int, str]
    neighbors_by_item: dict[int, list[tuple[int, float]]]
    item_vectors: np.ndarray | None
    meta: dict[str, Any]


def _resolve_artifact_root(root: str | Path | None = None) -> Path:
    if root is None:
        root = RECOMMENDER_ARTIFACTS_DIR
    path = Path(root)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[3] / path).resolve()


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "item_index": root / "item_index.parquet",
        "neighbors": root / "item_neighbors.parquet",
        "vectors": root / "item_vectors.npy",
        "meta": root / "meta.json",
    }


def artifacts_available(root: str | Path | None = None) -> bool:
    root_path = _resolve_artifact_root(root)
    paths = _artifact_paths(root_path)
    required = (paths["item_index"], paths["neighbors"], paths["meta"])
    return all(path.exists() for path in required)


def _load_recommender_artifacts(root: str | Path | None = None) -> RecommenderArtifacts | None:
    root_path = _resolve_artifact_root(root)
    paths = _artifact_paths(root_path)
    if not artifacts_available(root_path):
        return None
    try:
        item_idx_df = pd.read_parquet(paths["item_index"])
        required_idx_cols = {"catalog_key", "item_idx"}
        if not required_idx_cols.issubset(item_idx_df.columns):
            return None

        item_idx_df = item_idx_df.dropna(subset=["catalog_key", "item_idx"]).copy()
        item_idx_df["catalog_key"] = item_idx_df["catalog_key"].astype(str)
        item_idx_df["item_idx"] = pd.to_numeric(item_idx_df["item_idx"], errors="coerce").astype("Int64")
        item_idx_df = item_idx_df.dropna(subset=["item_idx"]).copy()
        item_idx_df["item_idx"] = item_idx_df["item_idx"].astype(int)

        item_index = dict(zip(item_idx_df["catalog_key"], item_idx_df["item_idx"]))
        index_to_key = {v: k for k, v in item_index.items()}

        neighbors_df = pd.read_parquet(paths["neighbors"])
        required_neighbor_cols = {"item_idx", "neighbor_idx", "sim"}
        if not required_neighbor_cols.issubset(neighbors_df.columns):
            return None

        neighbors_df = neighbors_df.dropna(subset=["item_idx", "neighbor_idx", "sim"]).copy()
        neighbors_df["item_idx"] = pd.to_numeric(neighbors_df["item_idx"], errors="coerce").astype("Int64")
        neighbors_df["neighbor_idx"] = pd.to_numeric(neighbors_df["neighbor_idx"], errors="coerce").astype("Int64")
        neighbors_df["sim"] = pd.to_numeric(neighbors_df["sim"], errors="coerce")
        neighbors_df = neighbors_df.dropna(subset=["item_idx", "neighbor_idx", "sim"]).copy()
        neighbors_df["item_idx"] = neighbors_df["item_idx"].astype(int)
        neighbors_df["neighbor_idx"] = neighbors_df["neighbor_idx"].astype(int)

        neighbors_by_item: dict[int, list[tuple[int, float]]] = {}
        for item_idx, grp in neighbors_df.groupby("item_idx", sort=False):
            sorted_grp = grp.sort_values("sim", ascending=False)
            neighbors_by_item[int(item_idx)] = [
                (int(row.neighbor_idx), float(row.sim))
                for row in sorted_grp.itertuples(index=False)
            ]

        item_vectors: np.ndarray | None = None
        if paths["vectors"].exists():
            vectors = np.load(paths["vectors"])
            if isinstance(vectors, np.ndarray) and vectors.ndim == 2:
                item_vectors = vectors.astype(np.float32)

        meta: dict[str, Any] = {}
        with paths["meta"].open("r", encoding="utf-8") as fh:
            maybe_meta = json.load(fh)
        if isinstance(maybe_meta, dict):
            meta = maybe_meta

        return RecommenderArtifacts(
            item_index=item_index,
            index_to_key=index_to_key,
            neighbors_by_item=neighbors_by_item,
            item_vectors=item_vectors,
            meta=meta,
        )
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def load_recommender_artifacts(root: str | None = None) -> RecommenderArtifacts | None:
    """Cached wrapper for artifact loading in Streamlit runtime."""
    return _load_recommender_artifacts(root)


def get_recommender_model_meta(root: str | Path | None = None) -> dict[str, Any]:
    artifacts = load_recommender_artifacts(str(root) if root is not None else None)
    if artifacts is None:
        return {}
    return dict(artifacts.meta)

"""Diversity reranking with Maximum Marginal Relevance (MMR)."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms <= 1e-12] = 1.0
    return vectors / norms


def _max_similarity(
    candidate_idx: int | None,
    selected_idxs: Iterable[int],
    vectors: np.ndarray,
) -> float:
    if candidate_idx is None:
        return 0.0
    selected_list = list(selected_idxs)
    if not selected_list:
        return 0.0
    if candidate_idx < 0 or candidate_idx >= vectors.shape[0]:
        return 0.0

    cand_vec = vectors[candidate_idx]
    sims: list[float] = []
    for idx in selected_list:
        if idx < 0 or idx >= vectors.shape[0]:
            continue
        sims.append(float(np.dot(cand_vec, vectors[idx])))
    if not sims:
        return 0.0
    return max(sims)


def rerank_mmr(
    ranked_candidates: pd.DataFrame,
    *,
    item_vectors: np.ndarray | None,
    item_index: dict[str, int],
    top_n: int,
    lambda_: float = 0.75,
) -> pd.DataFrame:
    """Apply greedy MMR reranking using CF item vectors."""
    if ranked_candidates.empty:
        return ranked_candidates.copy()

    top_n = max(int(top_n), 0)
    if top_n == 0:
        return ranked_candidates.head(0).copy()

    candidates = ranked_candidates.copy().reset_index(drop=True)
    candidates["_item_idx"] = candidates["catalog_key"].map(item_index)

    if item_vectors is None or not isinstance(item_vectors, np.ndarray) or item_vectors.ndim != 2:
        return candidates.head(top_n).drop(columns=["_item_idx"]).copy()

    vectors = _normalize_rows(item_vectors.astype(np.float32))
    lambda_ = float(max(0.0, min(1.0, lambda_)))

    selected_rows: list[int] = []
    selected_item_idxs: list[int] = []
    remaining_rows: set[int] = set(range(len(candidates)))

    while remaining_rows and len(selected_rows) < top_n:
        best_row: int | None = None
        best_score = -np.inf

        for row_idx in remaining_rows:
            row = candidates.iloc[row_idx]
            rel = float(row.get("score", 0.0))
            cand_item_idx = row.get("_item_idx")
            cand_item_idx_int = int(cand_item_idx) if pd.notna(cand_item_idx) else None
            redundancy = _max_similarity(cand_item_idx_int, selected_item_idxs, vectors)
            mmr_score = lambda_ * rel - (1.0 - lambda_) * redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_row = row_idx

        if best_row is None:
            break

        selected_rows.append(best_row)
        remaining_rows.remove(best_row)

        chosen_idx = candidates.iloc[best_row].get("_item_idx")
        if pd.notna(chosen_idx):
            selected_item_idxs.append(int(chosen_idx))

    if not selected_rows:
        return candidates.head(top_n).drop(columns=["_item_idx"]).copy()

    out = candidates.iloc[selected_rows].copy().reset_index(drop=True)
    return out.drop(columns=["_item_idx"])

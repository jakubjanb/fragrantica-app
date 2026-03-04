"""Final score construction for hybrid recommendations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _minmax01(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if vals.empty:
        return vals
    mn = float(vals.min())
    mx = float(vals.max())
    if not np.isfinite(mn) or not np.isfinite(mx) or mx - mn <= 1e-12:
        return pd.Series(np.zeros(len(vals), dtype=float), index=vals.index)
    return (vals - mn) / (mx - mn)


def rank_candidates(df_candidates: pd.DataFrame) -> pd.DataFrame:
    """
    Compute final rank score.

    Base formula:
        score = 0.70 * cf + 0.15 * cat_affinity + 0.15 * quality

    When CF is unavailable, non-CF weights are re-normalized.
    """
    if df_candidates.empty:
        return df_candidates.copy()

    ranked = df_candidates.copy()

    cf_raw = pd.to_numeric(ranked.get("cf_score"), errors="coerce").fillna(0.0)
    has_cf = bool((cf_raw.abs() > 1e-12).any())

    ranked["cf_norm"] = _minmax01(cf_raw) if has_cf else 0.0
    ranked["cat_norm"] = pd.to_numeric(ranked.get("cat_affinity"), errors="coerce").fillna(0.0).clip(0.0, 1.0)
    ranked["quality_norm"] = _minmax01(pd.to_numeric(ranked.get("quality_score"), errors="coerce").fillna(0.0))

    w_cf, w_cat, w_quality = 0.70, 0.15, 0.15
    if not has_cf:
        denom = w_cat + w_quality
        w_cf = 0.0
        w_cat = w_cat / denom
        w_quality = w_quality / denom

    ranked["cf_component"] = w_cf * ranked["cf_norm"]
    ranked["cat_component"] = w_cat * ranked["cat_norm"]
    ranked["quality_component"] = w_quality * ranked["quality_norm"]
    ranked["score"] = ranked["cf_component"] + ranked["cat_component"] + ranked["quality_component"]

    return ranked.sort_values("score", ascending=False, kind="mergesort").reset_index(drop=True)

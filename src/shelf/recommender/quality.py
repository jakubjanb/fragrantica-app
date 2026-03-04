"""Quality priors for recommendation ranking."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    std = float(vals.std(ddof=0))
    if not np.isfinite(std) or std <= 1e-12:
        return pd.Series(np.zeros(len(vals), dtype=float), index=vals.index)
    mean = float(vals.mean())
    return (vals - mean) / std


def _minmax01(series: pd.Series) -> pd.Series:
    vals = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    mn = float(vals.min()) if len(vals) else 0.0
    mx = float(vals.max()) if len(vals) else 0.0
    if not np.isfinite(mn) or not np.isfinite(mx) or mx - mn <= 1e-12:
        return pd.Series(np.zeros(len(vals), dtype=float), index=vals.index)
    return (vals - mn) / (mx - mn)


def compute_bayesian_quality(df_catalog: pd.DataFrame, C: float | None = None) -> pd.DataFrame:
    """
    Add robust item quality signals.

    Formula:
        q(i) = (v/(v+C))*R + (C/(v+C))*m
        quality_raw = z(q) + 0.3 * z(log(1+v))
    """
    catalog = df_catalog.copy()
    if catalog.empty:
        catalog["bayesian_rating"] = pd.Series(dtype="float64")
        catalog["quality_prior"] = pd.Series(dtype="float64")
        catalog["quality_score"] = pd.Series(dtype="float64")
        return catalog

    ratings = pd.to_numeric(catalog.get("rating"), errors="coerce")
    votes = pd.to_numeric(catalog.get("votes"), errors="coerce").fillna(0.0).clip(lower=0.0)

    valid_ratings = ratings.dropna()
    m = float(valid_ratings.mean()) if not valid_ratings.empty else 0.0

    if C is None:
        positive_votes = votes[votes > 0]
        C = float(positive_votes.median()) if not positive_votes.empty else 1.0
    if not np.isfinite(C) or C <= 0:
        C = 1.0

    safe_ratings = ratings.fillna(m)
    bayesian = (votes / (votes + C)) * safe_ratings + (C / (votes + C)) * m

    popularity = np.log1p(votes)
    quality_prior = _zscore(bayesian) + 0.3 * _zscore(popularity)
    quality_score = _minmax01(quality_prior)

    catalog["bayesian_rating"] = bayesian.astype(float)
    catalog["quality_prior"] = quality_prior.astype(float)
    catalog["quality_score"] = quality_score.astype(float)
    catalog["quality_global_mean"] = float(m)
    catalog["quality_prior_strength"] = float(C)
    return catalog

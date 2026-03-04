"""UI section for recommendations based on the user's shelf."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.shelf.constants import (
    ENABLE_RECOMMENDATION_LOG,
    RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA,
    RECOMMENDER_V2_ENABLED,
)
from src.shelf.domain import recommend
from src.shelf.recommender.pipeline import get_recommender_model_meta, set_runtime_options
from src.shelf.repository import _log_recommendations
from src.shelf.utils import _format_sex_label


def _normalize_link(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    link = str(value).strip()
    if not link or link.lower() in {"nan", "none"}:
        return None
    if link.startswith(("http://", "https://")):
        return link
    return None


def _render_recommendations(user_id: str, df_catalog: pd.DataFrame, df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Recommendations")
    st.markdown(
        '<p class="section-note">Get suggestions based on your shelf profile and audience preference.</p>',
        unsafe_allow_html=True,
    )
    if RECOMMENDER_V2_ENABLED:
        meta = get_recommender_model_meta()
        if meta:
            model_version = str(meta.get("model_version", "v2"))
            trained_at = str(meta.get("trained_at", "unknown"))
            st.caption(f"Model: {model_version} | Trained: {trained_at}")
        else:
            st.caption("Model: legacy fallback (Recommender V2 artifacts not found).")

    sex_options = {
        "Auto (from shelf)": "auto",
        "No preference": "any",
        "Women": "woman",
        "Unisex": "unisex",
        "Men": "men",
    }
    ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 2])
    with ctrl1:
        selected_sex_label = st.selectbox("Preferred audience", options=list(sex_options.keys()))
    with ctrl2:
        top_n = st.slider("Number of recommendations", min_value=5, max_value=20, value=10, step=1)
    with ctrl3:
        diversity_lambda = st.slider(
            "Diversity (MMR λ)",
            min_value=0.6,
            max_value=0.9,
            value=float(RECOMMENDER_DEFAULT_DIVERSITY_LAMBDA),
            step=0.05,
        )

    debug_mode = st.checkbox(
        "Debug scores",
        value=False,
        help="Show component scores (CF/category/quality/MMR inputs).",
    )
    set_runtime_options(debug=debug_mode, mmr_lambda=float(diversity_lambda))

    recs_df = recommend(
        df_catalog=df_catalog,
        df_shelf=df_shelf_enriched,
        user_pref_sex=sex_options[selected_sex_label],
        top_n=top_n,
    )

    if recs_df.empty:
        st.info("No recommendations yet. Add more fragrances to your shelf.")
        return

    view_df = recs_df.copy()
    if "score" in view_df.columns:
        view_df["score"] = pd.to_numeric(view_df["score"], errors="coerce").round(4)
    for col in ("cf_score", "cf_norm", "cat_affinity", "cat_norm", "quality_score", "quality_norm"):
        if col in view_df.columns:
            view_df[col] = pd.to_numeric(view_df[col], errors="coerce").round(4)

    if "url" in view_df.columns:
        view_df["Link"] = view_df["url"].apply(_normalize_link)
    elif "fragrance_id" in view_df.columns:
        view_df["Link"] = view_df["fragrance_id"].apply(_normalize_link)

    for raw_col in ("votes", "fragrance_id", "url"):
        if raw_col in view_df.columns:
            view_df = view_df.drop(columns=raw_col)

    view_df = view_df.rename(
        columns={
            "brand": "Brand",
            "name": "Fragrance",
            "sex": "Audience",
            "fragrance_category": "Category",
            "rating": "Rating",
            "family": "Family",
            "score": "Score",
            "cf_score": "CF raw",
            "cf_norm": "CF",
            "cat_affinity": "Cat affinity raw",
            "cat_norm": "Cat affinity",
            "quality_score": "Quality raw",
            "quality_norm": "Quality",
            "cf_component": "CF component",
            "cat_component": "Cat component",
            "quality_component": "Quality component",
            "sex_score": "Audience score",
            "bayesian_rating": "Bayesian rating",
            "quality_prior": "Quality prior z",
        }
    )
    if "Audience" in view_df.columns:
        view_df["Audience"] = view_df["Audience"].apply(_format_sex_label)

    column_config: dict[str, st.column_config.Column] = {}
    if "Link" in view_df.columns:
        column_config["Link"] = st.column_config.LinkColumn(
            "Link",
            display_text="Open",
        )

    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )

    if ENABLE_RECOMMENDATION_LOG:
        if st.button("Save recommendations to log"):
            try:
                _log_recommendations(user_id, recs_df)
                st.success("Recommendations saved to recommendation_log.")
            except Exception as exc:
                st.error(f"Could not save recommendation_log: {exc}")

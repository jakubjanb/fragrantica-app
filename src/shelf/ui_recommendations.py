"""UI section for recommendations based on the user's shelf."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.shelf.constants import ENABLE_RECOMMENDATION_LOG
from src.shelf.domain import recommend
from src.shelf.repository import _log_recommendations
from src.shelf.utils import _format_sex_label


def _render_recommendations(user_id: str, df_catalog: pd.DataFrame, df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Recommendations")
    st.markdown(
        '<p class="section-note">Get suggestions based on your shelf profile and audience preference.</p>',
        unsafe_allow_html=True,
    )

    sex_options = {
        "Auto (from shelf)": "auto",
        "No preference": "any",
        "Women": "woman",
        "Unisex": "unisex",
        "Men": "men",
    }
    ctrl1, ctrl2 = st.columns([3, 2])
    with ctrl1:
        selected_sex_label = st.selectbox("Preferred audience", options=list(sex_options.keys()))
    with ctrl2:
        top_n = st.slider("Number of recommendations", min_value=5, max_value=20, value=10, step=1)

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
    view_df = view_df.rename(
        columns={
            "brand": "Brand",
            "name": "Fragrance",
            "sex": "Audience",
            "fragrance_category": "Category",
            "rating": "Rating",
            "votes": "Votes",
            "family": "Family",
            "score": "Score",
        }
    )
    if "Audience" in view_df.columns:
        view_df["Audience"] = view_df["Audience"].apply(_format_sex_label)
    st.dataframe(view_df, use_container_width=True, hide_index=True)

    if ENABLE_RECOMMENDATION_LOG:
        if st.button("Save recommendations to log"):
            try:
                _log_recommendations(user_id, recs_df)
                st.success("Recommendations saved to recommendation_log.")
            except Exception as exc:
                st.error(f"Could not save recommendation_log: {exc}")

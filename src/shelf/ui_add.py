"""UI section for adding fragrances to the user's shelf."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.shelf.repository import add_to_shelf
from src.shelf.utils import _format_sex_label, _normalize_text


def _render_add_form(user_id: str, df_catalog: pd.DataFrame) -> None:
    st.subheader("Add fragrance")
    st.markdown(
        '<p class="section-note">Pick a brand, then select a fragrance to add to your shelf.</p>',
        unsafe_allow_html=True,
    )

    if df_catalog.empty:
        st.warning("The fragrance catalog is empty.")
        return

    catalog_df = df_catalog.copy()
    if "display_label" not in catalog_df.columns:
        catalog_df["display_label"] = (
            catalog_df.get("brand", "").fillna("").astype(str).str.strip()
            + " — "
            + catalog_df.get("name", "").fillna("").astype(str).str.strip()
        )

    for col in ("brand", "name", "fragrance_category", "sex", "rating", "votes"):
        if col not in catalog_df.columns:
            catalog_df[col] = pd.NA

    catalog_df["brand"] = catalog_df["brand"].fillna("").astype(str).str.strip()
    catalog_df["name"] = catalog_df["name"].fillna("").astype(str).str.strip()
    catalog_df["fragrance_category"] = catalog_df["fragrance_category"].fillna("").astype(str).str.strip()
    catalog_df["display_label"] = catalog_df["display_label"].fillna("").astype(str).str.strip()
    catalog_df = catalog_df.sort_values(by=["brand", "name"], ascending=[True, True], kind="mergesort")

    brands_list = sorted(
        [b for b in catalog_df["brand"].unique().tolist() if b],
        key=lambda v: v.casefold(),
    )

    add_submit = False
    include_rating = False
    rating = 7

    with st.container(border=True):
        selected_brand = st.selectbox(
            "Brand",
            options=[""] + brands_list,
            index=0,
            key="shelf_add_brand",
            help="Start typing to find a brand.",
            format_func=lambda b: "Select a brand…" if b == "" else b,
        )

        prev_brand = st.session_state.get("_shelf_add_prev_brand", "")
        if selected_brand != prev_brand:
            st.session_state["_shelf_add_prev_brand"] = selected_brand
            st.session_state.pop("shelf_add_selected_idx", None)

        if not selected_brand:
            st.caption(f"{len(brands_list):,} brands available — start typing above.")
            return

        brand_catalog = catalog_df[catalog_df["brand"] == selected_brand].copy()
        if brand_catalog.empty:
            st.info("No fragrances found for this brand.")
            return

        frag_count = len(brand_catalog)
        st.caption(f"{frag_count:,} fragrance{'s' if frag_count != 1 else ''} by {selected_brand}")

        option_indexes = brand_catalog.index.tolist()
        selected_idx_key = "shelf_add_selected_idx"
        if selected_idx_key in st.session_state and st.session_state[selected_idx_key] not in option_indexes:
            st.session_state.pop(selected_idx_key)

        selected_idx = st.selectbox(
            "Fragrance",
            options=option_indexes,
            key=selected_idx_key,
            format_func=lambda i: str(brand_catalog.at[i, "name"]),
            help="Start typing to find a fragrance.",
        )

        selected_item = brand_catalog.loc[int(selected_idx)]

        chips: list[str] = []
        selected_category = _normalize_text(selected_item.get("fragrance_category"))
        if selected_category:
            chips.append(selected_category)
        selected_sex_label = _format_sex_label(selected_item.get("sex"))
        if selected_sex_label:
            chips.append(selected_sex_label)
        fragrantica_rating = pd.to_numeric(pd.Series([selected_item.get("rating")]), errors="coerce").iloc[0]
        votes_value = pd.to_numeric(pd.Series([selected_item.get("votes")]), errors="coerce").iloc[0]
        if pd.notna(fragrantica_rating):
            rating_chip = f"★ {float(fragrantica_rating):.2f}"
            if pd.notna(votes_value):
                rating_chip += f" · {int(float(votes_value)):,} votes"
            chips.append(rating_chip)

        if chips:
            chips_html = "".join(
                f'<span class="meta-chip">{html.escape(c)}</span>' for c in chips
            )
            st.markdown(f'<div class="meta-row">{chips_html}</div>', unsafe_allow_html=True)

        chk_col, slider_col, btn_col = st.columns([1.5, 2.8, 1.2], vertical_alignment="center")
        with chk_col:
            include_rating = st.checkbox("My rating", value=False, key="shelf_add_include_rating")
        with slider_col:
            rating = st.slider(
                "Rating (1–10)",
                1,
                10,
                7,
                key="shelf_add_rating",
                disabled=not include_rating,
            )
        with btn_col:
            add_submit = st.button(
                "Add to shelf",
                use_container_width=True,
                type="primary",
                key="shelf_add_submit",
            )

    if add_submit:
        item = brand_catalog.loc[int(selected_idx)].to_dict()
        value = int(rating) if include_rating else None
        ok, message = add_to_shelf(user_id, item, value)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.warning(message)

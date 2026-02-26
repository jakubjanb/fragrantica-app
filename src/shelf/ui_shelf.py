"""UI section for reviewing and editing shelf items."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.shelf.domain import _coerce_user_rating, _sort_shelf_default, compute_family
from src.shelf.repository import delete_shelf_item, update_shelf_rating
from src.shelf.utils import _normalize_text


def _render_shelf_list(df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Your shelf")
    st.markdown(
        '<p class="section-note">Review and update your full shelf in one compact list.</p>',
        unsafe_allow_html=True,
    )

    feedback = st.session_state.pop("shelf_save_feedback", None)
    if feedback:
        st.success(feedback)

    feedback_errors = st.session_state.pop("shelf_save_errors", None)
    if feedback_errors:
        details = "\n- ".join(str(msg) for msg in feedback_errors)
        st.error(f"Some changes could not be saved:\n- {details}")

    if df_shelf_enriched.empty:
        st.info("Your shelf is empty. Add your first fragrance above.")
        return

    shelf_df = df_shelf_enriched.copy()
    for col in ("id", "brand", "name", "fragrance_category", "sex", "user_rating", "rating", "votes"):
        if col not in shelf_df.columns:
            shelf_df[col] = pd.NA

    shelf_df["__row_id"] = shelf_df["id"].apply(_normalize_text)
    invalid_ids = int((shelf_df["__row_id"] == "").sum())
    if invalid_ids:
        st.warning(f"{invalid_ids} shelf item(s) are missing IDs and cannot be edited.")
        shelf_df = shelf_df[shelf_df["__row_id"] != ""].copy()
        if shelf_df.empty:
            return

    shelf_df["Brand"] = shelf_df["brand"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Fragrance"] = shelf_df["name"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Category"] = shelf_df["fragrance_category"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Group"] = shelf_df["fragrance_category"].apply(compute_family)

    your_rating = pd.to_numeric(shelf_df["user_rating"], errors="coerce")
    shelf_df["Your rating"] = your_rating.where(your_rating.between(1, 10)).round().astype("Int64")

    search_query = st.text_input(
        "Search",
        key="shelf_table_search",
        placeholder="Brand, fragrance, category, or group",
    ).strip()

    filtered_df = shelf_df.copy()
    if search_query:
        q = search_query.lower()
        search_blob = (
            filtered_df["Brand"].str.lower()
            + " "
            + filtered_df["Fragrance"].str.lower()
            + " "
            + filtered_df["Category"].str.lower()
            + " "
            + filtered_df["Group"].str.lower()
        )
        filtered_df = filtered_df[search_blob.str.contains(q, na=False)].copy()

    filtered_df = _sort_shelf_default(filtered_df)
    st.caption(f"Showing {len(filtered_df)} of {len(shelf_df)} fragrances")

    if filtered_df.empty:
        st.info("No shelf items match your search.")
        return

    original_ratings = {
        str(row_id): (None if pd.isna(val) else int(val))
        for row_id, val in zip(filtered_df["__row_id"], filtered_df["Your rating"])
    }

    editor_df = filtered_df[
        [
            "__row_id",
            "Brand",
            "Fragrance",
            "Group",
            "Category",
            "Your rating",
        ]
    ].copy()
    editor_df["Remove"] = False
    editor_df = editor_df.set_index("__row_id")
    editor_df.index.name = "row_id"
    editor_df["Your rating"] = pd.to_numeric(editor_df["Your rating"], errors="coerce")

    table_height = min(900, 38 + len(editor_df) * 35 + 2)
    # Streamlit data_editor does not support Top-10-style HTML/styler bars on
    # editable cells, so "Your rating" remains a numeric editable field.
    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        height=table_height,
        key="shelf_table_editor",
        column_order=["Brand", "Fragrance", "Group", "Category", "Your rating", "Remove"],
        disabled=[
            "Brand",
            "Fragrance",
            "Group",
            "Category",
        ],
        column_config={
            "Your rating": st.column_config.NumberColumn(
                "Your rating",
                min_value=1,
                max_value=10,
                step=1,
                format="%d",
                required=False,
                help="Set personal rating from 1 to 10 or leave empty.",
            ),
            "Remove": st.column_config.CheckboxColumn("Remove"),
        },
    )

    if st.button("Save changes", type="primary", key="save_shelf_changes"):
        updated_count = 0
        removed_count = 0
        errors: list[str] = []

        for row_id, row in edited_df.iterrows():
            row_id_s = str(row_id)
            row_label = f"{row.get('Brand', '-')} — {row.get('Fragrance', '-')}"

            if bool(row.get("Remove", False)):
                ok, message = delete_shelf_item(row_id_s)
                if ok:
                    removed_count += 1
                else:
                    errors.append(f"{row_label}: {message}")
                continue

            new_rating, validation_error = _coerce_user_rating(row.get("Your rating"))
            if validation_error:
                errors.append(f"{row_label}: {validation_error}")
                continue

            old_rating = original_ratings.get(row_id_s)
            if new_rating == old_rating:
                continue

            ok, message = update_shelf_rating(row_id_s, new_rating)
            if ok:
                updated_count += 1
            else:
                errors.append(f"{row_label}: {message}")

        if updated_count == 0 and removed_count == 0 and not errors:
            st.info("No changes to save.")
            return

        summary_parts: list[str] = []
        if updated_count:
            summary_parts.append(f"Saved {updated_count} rating{'s' if updated_count != 1 else ''}")
        if removed_count:
            summary_parts.append(f"Removed {removed_count} fragrance{'s' if removed_count != 1 else ''}")

        if summary_parts:
            st.session_state["shelf_save_feedback"] = ", ".join(summary_parts)
        if errors:
            st.session_state["shelf_save_errors"] = errors[:8]
        st.rerun()

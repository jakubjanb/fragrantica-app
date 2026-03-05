"""
Subpage: Fragrance Shelf

MVP features:
- Supabase auth (email/password)
- User shelf CRUD (public.user_shelf)
- Simple content-based recommendations
- Fragrance wheel family coverage
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from src.shelf.auth import auth_block
from src.shelf.catalog import load_catalog_df
from src.shelf.domain import _enrich_shelf_with_catalog
from src.shelf.repository import fetch_user_shelf
from src.shelf.styles import _inject_page_styles
from src.shelf.ui_add import _render_add_form
from src.shelf.ui_coverage import _render_coverage
from src.shelf.ui_recommendations import _render_recommendations
from src.shelf.ui_shelf import _render_shelf_list


def _build_icon_tag(filename: str, fallback_emoji: str) -> str:
    icon_path = Path(__file__).resolve().parent.parent / "Graphics" / filename
    if not icon_path.exists():
        return fallback_emoji

    try:
        icon_data = base64.b64encode(icon_path.read_bytes()).decode("utf-8")
    except OSError:
        return fallback_emoji

    return (
        '<img src="data:image/png;base64,'
        f'{icon_data}" width="44" style="vertical-align: middle; display: inline-block;">'
    )


def _render_title_with_icon(title: str, icon_tag: str) -> None:
    st.markdown(
        f'<h1 style="display:flex;align-items:center;gap:0.55rem;margin:0 0 0.25rem 0;">'
        f"<span>{icon_tag}</span><span>{title}</span></h1>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Fragrance Shelf",
        page_icon="👤",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_page_styles()
    shelf_icon_tag = _build_icon_tag("fragrance_shelf.png", "👤")
    _render_title_with_icon("Your Fragrance Shelf", shelf_icon_tag)
    subtitle_html = (
        '<p class="subtitle">Build your personal shelf, save your ratings, and discover '
        "recommendations tailored to your collection.</p>"
    )

    if st.session_state.get("auth_user_id"):
        intro_col, account_col = st.columns([4.2, 3.0], gap="large")
        with intro_col:
            st.markdown(subtitle_html, unsafe_allow_html=True)
        with account_col:
            user_id = auth_block(compact_logged_in=True)
    else:
        st.markdown(subtitle_html, unsafe_allow_html=True)
        user_id = None

    try:
        df_catalog = load_catalog_df()
    except Exception as exc:
        st.error(f"Could not load fragrance catalog: {exc}")
        return

    if not user_id:
        user_id = auth_block()

    if not user_id:
        st.info("Sign in to save your shelf and get personalized recommendations.")
        return

    st.divider()

    try:
        df_shelf = fetch_user_shelf(user_id)
    except Exception as exc:
        st.error(f"Could not fetch your shelf data: {exc}")
        return

    _render_add_form(user_id, df_catalog)

    try:
        df_shelf_enriched = _enrich_shelf_with_catalog(df_shelf, df_catalog)
    except Exception as exc:
        st.error(f"Could not join shelf data with catalog: {exc}")
        df_shelf_enriched = df_shelf.copy()

    _render_shelf_list(df_shelf_enriched)
    st.divider()
    _render_coverage(df_shelf_enriched)
    st.divider()
    _render_recommendations(user_id, df_catalog, df_shelf_enriched)


if __name__ == "__main__":
    main()

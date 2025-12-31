from __future__ import annotations

from typing import Iterable, List, Optional

import streamlit as st


def brand_selector(options: Iterable[str], default: Optional[str] = None) -> str:
    """Render a brand select widget with search functionality in Streamlit sidebar/body.

    Returns the selected brand.
    """
    opts: List[str] = list(options)
    if not opts:
        st.warning("No brands to select.")
        return ""

    # Render controls on the same row with equal widths:
    # - left: Select brand (dropdown)
    # - right: Search brand (text input)
    col_select, col_search = st.columns([2, 2])

    # Put search input on the right column (but read its value before building filtered options)
    with col_search:
        search_query = st.text_input(
            "Search brand",
            placeholder="Type to filter brands...",
            help="Start typing to quickly find your brand",
        )

    # Filter options based on search query
    if search_query:
        filtered_opts = [opt for opt in opts if search_query.lower() in opt.lower()]
        if not filtered_opts:
            st.info(f"No brands found matching '{search_query}'")
            filtered_opts = opts
    else:
        filtered_opts = opts

    index = 0
    if default in filtered_opts:
        index = filtered_opts.index(default)  # type: ignore[arg-type]

    # Put selectbox on the left column
    with col_select:
        return st.selectbox(
            "Select brand",
            options=filtered_opts,
            index=index,
            help="Choose a brand to visualize",
        )

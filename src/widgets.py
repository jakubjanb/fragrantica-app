from __future__ import annotations

from typing import Iterable, List, Optional

import streamlit as st


def _brand_bucket(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "#"
    ch = v[0]
    if ch.isalpha():
        return ch.upper()
    if ch.isdigit():
        return "0-9"
    return "#"


def brand_selector(options: Iterable[str], default: Optional[str] = None) -> str:
    """Render a brand select widget in Streamlit sidebar/body.

    Returns the selected brand.
    """
    opts: List[str] = list(options)
    if not opts:
        st.warning("No brands to select.")
        return ""

    # --- First-letter filter (shown above the selectbox) ---
    buckets_present = {_brand_bucket(o) for o in opts}
    letters = sorted([b for b in buckets_present if len(b) == 1 and b.isalpha()])
    special = []
    if "0-9" in buckets_present:
        special.append("0-9")
    if "#" in buckets_present:
        special.append("#")

    bucket_options = ["All", *letters, *special]

    # Default the filter to the default brand's bucket (only on first render).
    filter_key = "brand_letter_filter"
    if filter_key not in st.session_state:
        if default is not None:
            st.session_state[filter_key] = _brand_bucket(default)
            if st.session_state[filter_key] not in bucket_options:
                st.session_state[filter_key] = "All"
        else:
            st.session_state[filter_key] = "All"

    selected_bucket = st.radio(
        "Filter by first letter",
        options=bucket_options,
        key=filter_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    if selected_bucket != "All":
        filtered_opts = [o for o in opts if _brand_bucket(o) == selected_bucket]
    else:
        filtered_opts = opts

    if not filtered_opts:
        st.info("No brands match the selected filter.")
        return ""

    index = 0
    if default in filtered_opts:
        index = filtered_opts.index(default)  # type: ignore[arg-type]

    return st.selectbox(
        "Select brand",
        options=filtered_opts,
        index=index,
        help="Choose a brand to visualize",
    )

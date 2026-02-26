"""
Subpage: Fragrance Explorer

This page contains the full explorer UI that used to live in app.py.
"""

import math
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.data import load_data, list_brands
from src.widgets import brand_selector
from src.plots import make_figure
from src.tables import render_top_fragrances_table


def main() -> None:
    st.set_page_config(
        page_title="Fragrance Explorer",
        page_icon="🧴",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- CSS STYLING ---
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --border-subtle: #e5e7eb;
            --text-strong: #111827;
            --text-muted: #64748b;
            --accent: #0f766e;
            --accent-hover: #115e59;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa;
            transition: width 0.3s ease, min-width 0.3s ease, margin-left 0.3s ease;
        }

        /* When sidebar is expanded, reserve its width */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            width: 320px !important;
            min-width: 320px !important;
        }

        /* When sidebar is collapsed, free all reserved space */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
            margin-left: 0 !important;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 2rem;
        }

        /* Dropdown menu height */
        div[data-baseweb="popover"] ul,
        ul[data-baseweb="menu"],
        div[role="listbox"] ul {
            max-height: 400px !important;
        }

        /* Main content centering and transition */
        .main .block-container {
            max-width: 100%;
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 1.5rem;
            padding-bottom: 1rem;
            transition: margin-left 0.3s ease;
        }

        /* Ensure main content always uses available width */
        section[data-testid="stSidebar"] ~ .main .block-container { margin-left: 0 !important; }

        /* Title styling */
        h1 {
            color: #1f2937;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        /* Subtitle styling */
        .subtitle {
            color: #6b7280;
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }

        .toolbar-note {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin: 0.25rem 0 0.75rem;
        }

        /* Sidebar header */
        section[data-testid="stSidebar"] h2 {
            color: #374151;
            font-size: 1.3rem;
            margin-bottom: 1.5rem;
            font-weight: 600;
        }

        /* Input fields */
        .stTextInput input {
            border-radius: 6px;
            border: 1px solid #d1d5db;
        }

        .stTextInput input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 1px #3b82f6;
        }

        /* Plot container */
        iframe {
            display: block;
            width: 100% !important;
            border-radius: 8px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 0.8rem 1rem;
            min-height: 128px;
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--text-muted);
            font-weight: 500;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text-strong);
        }

        div[data-testid="stButton"] > button {
            border-radius: 999px;
            font-weight: 600;
            min-height: 2.75rem;
            border: 1px solid #cbd5e1;
            background: var(--surface);
            color: var(--text-strong);
            width: 100%;
        }

        div[data-testid="stButton"] > button:hover {
            border-color: #94a3b8;
            background: #f8fafc;
            color: var(--text-strong);
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background: var(--accent);
            border-color: var(--accent);
            color: #ffffff;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
            color: #ffffff;
        }

        div[data-testid="stToggle"] label p {
            font-weight: 600;
            color: var(--text-strong);
        }

        /* Base column transitions */
        [data-testid="column"] {
            transition: all 0.3s ease;
        }

        @media (max-width: 980px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🧴 Fragrance Explorer")
    st.markdown(
        '<p class="subtitle">Explore perfume ratings and votes by brand. Use the selector below to choose a brand, then view its perfumes plotted by rating and popularity.</p>',
        unsafe_allow_html=True,
    )

    # Resolve the CSV path relative to the project root (this file is under pages/)
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "Data" / "all_brands_clean.csv"

    if not csv_path.exists():
        st.error(f"Data file not found: {csv_path}")
        st.stop()

    df = load_data(csv_path)

    if df.empty:
        st.warning("No data available after cleaning.")
        st.stop()

    brands = list_brands(df)
    if not brands:
        st.warning("No brands found in the dataset.")
        st.stop()

    # --- Brand selector placed in main content (compact header row) ---
    # Make the selector row wider (approximately 2x wider than before)
    # Previously: [1.2, 3] -> ~28.6% width for the selector area.
    # Now: [4, 3] -> ~57.1% width, effectively doubling the available space.
    sel_col, _ = st.columns([4, 3])
    with sel_col:
        selected_brand = brand_selector(brands, default=None)

    # Keep helpful tip in the sidebar (no selector here)
    with st.sidebar:
        st.markdown("### 💡 Tip")
        st.markdown("Click on any data point to open the perfume's Fragrantica page.")

    # --- Sex filter state (initialise once; persists across reruns) ---
    for _k, _v in [("sex_women", True), ("sex_unisex", True), ("sex_men", True)]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # On first load and on brand change, start with all sex segments selected.
    brand_changed = st.session_state.get("prev_brand") != selected_brand
    if brand_changed:
        st.session_state.sex_women = True
        st.session_state.sex_unisex = True
        st.session_state.sex_men = True
        st.session_state.show_all = False
        st.session_state.prev_brand = selected_brand

    brand_all_df = df[df["brand"] == selected_brand].copy()
    sex_counts = {
        "women": int((brand_all_df["sex"] == "women").sum()),
        "unisex": int((brand_all_df["sex"] == "unisex").sum()),
        "men": int((brand_all_df["sex"] == "men").sum()),
    }

    # Keep unavailable segments off for current brand.
    if sex_counts["women"] == 0:
        st.session_state.sex_women = False
    if sex_counts["unisex"] == 0:
        st.session_state.sex_unisex = False
    if sex_counts["men"] == 0:
        st.session_state.sex_men = False

    # Ensure at least one available segment remains active.
    if any(sex_counts.values()) and not any(
        [st.session_state.sex_women, st.session_state.sex_unisex, st.session_state.sex_men]
    ):
        if sex_counts["women"] > 0:
            st.session_state.sex_women = True
        elif sex_counts["unisex"] > 0:
            st.session_state.sex_unisex = True
        else:
            st.session_state.sex_men = True

    selected_sexes = (
        (["women"] if st.session_state.sex_women else [])
        + (["unisex"] if st.session_state.sex_unisex else [])
        + (["men"] if st.session_state.sex_men else [])
    )

    # --- Summary metrics and filters ---
    brand_df = brand_all_df[brand_all_df["sex"].isin(selected_sexes)]
    total_frags = int(len(brand_df))
    # Guard against empty slice; ratings are coerced to numeric in load_data
    if total_frags > 0:
        high_rating_count = int((brand_df["rating"] >= 4.0).sum())
        pct_high = high_rating_count / total_frags
        total_votes = float(brand_df["votes"].sum())
        if total_votes > 0:
            weighted_avg_rating = float((brand_df["rating"] * brand_df["votes"]).sum() / total_votes)
            weighted_avg_rating_display = f"{weighted_avg_rating:.2f}"
        else:
            weighted_avg_rating_display = "N/A"
    else:
        high_rating_count = 0
        pct_high = 0.0
        weighted_avg_rating_display = "N/A"

    # --- Vote threshold filter (show top fragrances by default) ---

    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric(label="Number of fragrances", value=f"{total_frags}")
    with mcol2:
        st.metric(label="Rating ≥ 4.0", value=f"{pct_high:.1%}")
    with mcol3:
        st.metric(label="Weighted avg rating", value=weighted_avg_rating_display)

    st.markdown('<p class="toolbar-note">Metrics are calculated within current filters.</p>', unsafe_allow_html=True)

    ctrl0, ctrl1, ctrl2, ctrl3 = st.columns([2.2, 1, 1, 1])
    active_segments = int(st.session_state.sex_women) + int(st.session_state.sex_unisex) + int(st.session_state.sex_men)
    blocked_last_segment_toggle = False

    with ctrl0:
        st.toggle("👁 Show all fragrances", key="show_all")

    with ctrl1:
        women_label = f"Women ({sex_counts['women']})"
        if st.button(
            women_label,
            key="women_filter",
            type="primary" if st.session_state.sex_women else "secondary",
            disabled=sex_counts["women"] == 0,
        ):
            if st.session_state.sex_women and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.sex_women = not st.session_state.sex_women
                st.rerun()

    with ctrl2:
        unisex_label = f"Unisex ({sex_counts['unisex']})"
        if st.button(
            unisex_label,
            key="unisex_filter",
            type="primary" if st.session_state.sex_unisex else "secondary",
            disabled=sex_counts["unisex"] == 0,
        ):
            if st.session_state.sex_unisex and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.sex_unisex = not st.session_state.sex_unisex
                st.rerun()

    with ctrl3:
        men_label = f"Men ({sex_counts['men']})"
        if st.button(
            men_label,
            key="men_filter",
            type="primary" if st.session_state.sex_men else "secondary",
            disabled=sex_counts["men"] == 0,
        ):
            if st.session_state.sex_men and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.sex_men = not st.session_state.sex_men
                st.rerun()

    # Filter low-vote fragrances for the plot:
    # use 30th percentile by default, but stricter 50th percentile for very high-volume brands.
    brand_total_votes = float(brand_all_df["votes"].sum()) if not brand_all_df.empty else 0.0
    vote_quantile = 0.50 if brand_total_votes > 150_000 else 0.30
    vote_threshold = float(brand_df["votes"].quantile(vote_quantile)) if total_frags > 0 else 0.0

    if not st.session_state.show_all:
        shown = int((brand_df["votes"] >= vote_threshold).sum()) if total_frags > 0 else 0
        status_text = f"Showing {shown} of {total_frags} fragrances (votes ≥ {vote_threshold:.0f})"
        mask = (df["brand"] == selected_brand) & (df["sex"].isin(selected_sexes)) & (df["votes"] >= vote_threshold)
        df_plot = df[mask | (df["brand"] != selected_brand)].copy()
    else:
        status_text = f"Showing all {total_frags} fragrances"
        df_plot = df[df["sex"].isin(selected_sexes) | (df["brand"] != selected_brand)].copy()

    status_col, warn_col = st.columns([2.2, 3])
    with status_col:
        st.caption(status_text)
    with warn_col:
        if blocked_last_segment_toggle:
            st.caption("At least one segment must stay active.")

    # Create centered plot container
    fig = make_figure(df_plot, selected_brand)

    # Render Plotly with a click handler to open the perfume URL in a new tab
    # The figure contains custom_data=["url"] for each point (set in plots.make_figure)
    html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        div_id="fragrance-plot",
        config={
            'responsive': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
        }
    )

    click_js = """
    <script>
    (function attachClick(){
      var gd = document.getElementById('fragrance-plot');
      // If Plotly hasn't initialized yet, try again on next frame
      if (!gd || typeof gd.on !== 'function') { requestAnimationFrame(attachClick); return; }

      function resizePlot() {
        try {
          if (gd && typeof Plotly !== 'undefined' && Plotly.Plots && Plotly.Plots.resize) {
            Plotly.Plots.resize(gd);
          }
        } catch (e) {}
      }

      // 1) React to browser resize
      window.addEventListener('resize', resizePlot);

      // 2) React to container/iframe size changes (sidebar collapse expands main area)
      // This is more reliable than observing the parent sidebar DOM (not accessible from iframe).
      if (typeof ResizeObserver !== 'undefined') {
        var ro = new ResizeObserver(function() { resizePlot(); });
        ro.observe(document.documentElement);
      } else {
        // Fallback: periodically check width changes
        var lastW = document.documentElement.clientWidth;
        setInterval(function() {
          var w = document.documentElement.clientWidth;
          if (w !== lastW) { lastW = w; resizePlot(); }
        }, 300);
      }

      gd.on('plotly_click', function(data){
        try {
          var url = data && data.points && data.points[0] && data.points[0].customdata;
          if (Array.isArray(url)) { url = url[0]; }
          if (url && typeof url === 'string' && /^https?:\\/\\//.test(url)) {
            window.open(url, '_blank', 'noopener');
          }
        } catch (e) { console && console.log && console.log(e); }
      });

      // Initial resize after mount
      setTimeout(resizePlot, 0);
      setTimeout(resizePlot, 300);
    })();
    </script>
    """

    # Render full-width so it naturally expands when the sidebar collapses
    components.html(html + click_js, height=950, scrolling=False)

    st.markdown("### Top 10 fragrances")
    rank_mode = st.radio(
        "Ranking mode",
        options=["Reliable top-rated", "Raw rating"],
        index=0,
        horizontal=True,
        key="fragrance_top10_mode",
        help="Reliable mode ranks with a confidence-aware score. Raw mode ranks by rating only.",
    )

    min_votes_threshold = int(math.ceil(vote_threshold)) if total_frags > 0 else 0
    percentile_label = int(vote_quantile * 100)
    st.caption(
        f"Top-rated (min {min_votes_threshold:,} votes; {percentile_label}th percentile threshold for current brand filters)"
    )

    table_pool = brand_df[brand_df["votes"] >= min_votes_threshold].copy()
    if table_pool.empty:
        st.info("No fragrances meet the current minimum-votes threshold.")
    else:
        # Bayesian-style shrinkage balances rating quality with vote confidence.
        prior_rating = float(brand_df["rating"].mean()) if not brand_df.empty else 0.0
        m = float(min_votes_threshold)
        if m > 0:
            v = table_pool["votes"].astype(float)
            r = table_pool["rating"].astype(float)
            table_pool["reliable_score"] = (v / (v + m)) * r + (m / (v + m)) * prior_rating
        else:
            table_pool["reliable_score"] = table_pool["rating"].astype(float)

        if rank_mode == "Reliable top-rated":
            table_pool = table_pool.sort_values(
                ["reliable_score", "rating", "votes"],
                ascending=[False, False, False],
            )
        else:
            table_pool = table_pool.sort_values(
                ["rating", "votes"],
                ascending=[False, False],
            )

        top10_df = table_pool.head(10).copy().reset_index(drop=True)
        top10_df["Rank"] = top10_df.index + 1
        top10_df["Sex"] = top10_df["sex"].fillna("-").astype(str).str.capitalize()
        top10_df["Category"] = top10_df["fragrance_category"].fillna("-").astype(str)

        display_top10 = top10_df[
            ["Rank", "name", "rating", "votes", "Sex", "Category", "url"]
        ].rename(
            columns={
                "name": "Fragrance",
                "rating": "Rating",
                "votes": "Votes",
                "url": "Link",
            }
        )
        render_top_fragrances_table(display_top10)


if __name__ == "__main__":
    main()

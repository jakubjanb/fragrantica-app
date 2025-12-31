"""
Subpage: Fragrance Explorer

This page contains the full explorer UI that used to live in app.py.
"""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.data import load_data, list_brands
from src.widgets import brand_selector
from src.plots import make_figure


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

        /* Make columns responsive */
        [data-testid="column"] {
            transition: all 0.3s ease;
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
        selected_brand = brand_selector(brands, default=brands[0])

    # Keep helpful tip in the sidebar (no selector here)
    with st.sidebar:
        st.markdown("### 💡 Tip")
        st.markdown("Click on any point to open the perfume's Fragrantica page.")

    # --- Summary metrics above the plot ---
    brand_df = df[df["brand"] == selected_brand]
    total_frags = int(len(brand_df))
    # Guard against empty slice; ratings are coerced to numeric in load_data
    if total_frags > 0:
        high_rating_count = int((brand_df["rating"] >= 4.0).sum())
        pct_high = high_rating_count / total_frags
    else:
        high_rating_count = 0
        pct_high = 0.0

    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.metric(label="Number of fragrances", value=f"{total_frags}")
    with mcol2:
        st.metric(label="Rating ≥ 4.0", value=f"{pct_high:.1%}")

    # Create centered plot container
    fig = make_figure(df, selected_brand)

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
          if (url && typeof url === 'string' && /^https?:\/\//.test(url)) {
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


if __name__ == "__main__":
    main()

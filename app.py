"""
Streamlit app: Fragrance World (Landing Page)

Usage:
    streamlit run app.py

This is the landing page for the Fragrance World app. Use the navigation to open subpages.
"""

import base64
from pathlib import Path

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="Fragrance World",
        page_icon="🧴",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── Custom CSS ──────────────────────────────────────────────────
    st.markdown(
        """
        <style>
        /* Hero */
        .hero-title {
            font-size: 2.8rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }
        .hero-subtitle {
            font-size: 1.15rem;
            color: #6b7280;
            line-height: 1.65;
            max-width: 920px;
        }

        /* Launch buttons */
        .launch-btn {
            display: block;
            background: linear-gradient(135deg, #f8faff 0%, #eef2ff 100%);
            border: 2px solid #e0e7ff;
            border-radius: 16px;
            padding: 1.8rem 1.6rem;
            text-decoration: none !important;
            color: inherit !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
        }
        .launch-btn:hover {
            border-color: #818cf8;
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.15);
            transform: translateY(-3px);
            background: linear-gradient(135deg, #f0f4ff 0%, #e8edff 100%);
        }
        .launch-btn:active {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.12);
        }
        .launch-btn .lb-icon {
            font-size: 2.4rem;
            margin-bottom: 0.6rem;
        }
        .launch-btn .lb-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.35rem;
        }
        .launch-btn .lb-desc {
            font-size: 0.88rem;
            color: #64748b;
            line-height: 1.5;
        }
        .launch-btn .lb-arrow {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            margin-top: 0.9rem;
            font-size: 0.85rem;
            font-weight: 600;
            color: #6366f1;
            transition: gap 0.2s ease;
        }
        .launch-btn:hover .lb-arrow {
            gap: 0.55rem;
        }

        /* Launch button color variants */
        .launch-btn.variant-b {
            background: linear-gradient(135deg, #f8fffe 0%, #ecfdf5 100%);
            border-color: #d1fae5;
        }
        .launch-btn.variant-b:hover {
            border-color: #34d399;
            box-shadow: 0 8px 30px rgba(52, 211, 153, 0.15);
            background: linear-gradient(135deg, #f0fdf8 0%, #e6fbf0 100%);
        }
        .launch-btn.variant-b .lb-arrow {
            color: #059669;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero ────────────────────────────────────────────────────────
    # Load and encode the perfume emoji image
    img_path = Path(__file__).parent / "Graphics" / "perfume_emoji.png"
    if img_path.exists():
        with open(img_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{img_data}" width="50" style="vertical-align: middle; margin-right: 10px;">'
    else:
        img_tag = "🧴"  # Fallback to emoji if image not found

    st.markdown("")
    col_hero, _ = st.columns([3, 1])
    with col_hero:
        st.markdown(f'<div class="hero-title">{img_tag} Fragrance World</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-subtitle">'
            "Interactive dashboards for exploring perfume ratings, brand positioning, and popularity — powered by Fragrantica."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Quick-launch row ────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown(
            """
            <a href="/fragrance_explorer" target="_self" class="launch-btn">
                <div class="lb-icon">🔍</div>
                <div class="lb-title">Fragrance Explorer</div>
                <div class="lb-desc">
                    Browse perfumes by brand — filter, compare ratings &amp; votes on an interactive scatter chart.
                </div>
                <div class="lb-arrow">Open Explorer →</div>
            </a>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            """
            <a href="/brands_landscape" target="_self" class="launch-btn variant-b">
                <div class="lb-icon">🗺️</div>
                <div class="lb-title">Brands Landscape</div>
                <div class="lb-desc">
                    Compare all brands on quality vs. popularity plot, find key data insights.
                </div>
                <div class="lb-arrow">Open Landscape →</div>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Sidebar ─────────────────────────────────────────────────────
    with st.sidebar:
        st.caption("Built with Streamlit & Plotly · Data from Fragrantica")


if __name__ == "__main__":
    main()
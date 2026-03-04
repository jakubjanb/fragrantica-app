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

        .launch-btn.variant-c {
            background: linear-gradient(135deg, #fffbf5 0%, #fef3e2 100%);
            border-color: #fed7aa;
        }
        .launch-btn.variant-c:hover {
            border-color: #fb923c;
            box-shadow: 0 8px 30px rgba(251, 146, 60, 0.15);
            background: linear-gradient(135deg, #fff8f0 0%, #feecd6 100%);
        }
        .launch-btn.variant-c .lb-arrow {
            color: #ea580c;
        }

        .launch-btn.variant-d {
            background: linear-gradient(135deg, #fdf5ff 0%, #f3e8ff 100%);
            border-color: #e9d5ff;
        }
        .launch-btn.variant-d:hover {
            border-color: #a855f7;
            box-shadow: 0 8px 30px rgba(168, 85, 247, 0.15);
            background: linear-gradient(135deg, #faf0ff 0%, #ede3ff 100%);
        }
        .launch-btn.variant-d .lb-arrow {
            color: #9333ea;
        }

        /* Tighten gap between button rows */
        .btn-row-gap {
            margin-top: -0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def load_icon_tag(filename: str, fallback_emoji: str) -> str:
        icon_path = Path(__file__).parent / "Graphics" / filename
        if icon_path.exists():
            with open(icon_path, "rb") as f:
                icon_data = base64.b64encode(f.read()).decode()
            return (
                f'<img src="data:image/png;base64,{icon_data}" width="50" '
                'style="vertical-align: middle;" alt="">'
            )
        return fallback_emoji

    # ── Hero ────────────────────────────────────────────────────────
    # Load and encode the perfume emoji image
    img_path = Path(__file__).parent / "Graphics" / "perfume_emoji.png"
    if img_path.exists():
        with open(img_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{img_data}" width="50" style="vertical-align: middle; margin-right: 10px;">'
    else:
        img_tag = "🧴"  # Fallback to emoji if image not found

    wheel_icon_tag = load_icon_tag("fragrance_wheel.png", "🏷️")
    shelf_icon_tag = load_icon_tag("fragrance_shelf.png", "👤")

    st.markdown("")
    col_hero, _ = st.columns([3, 1])
    with col_hero:
        st.markdown(f'<div class="hero-title">{img_tag} Fragrance World</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-subtitle">'
            "Interactive dashboards for exploring perfume ratings, brand positioning, fragrance families, and personalized recommendations."
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Quick-launch grid (2 × 2) ───────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown(
            """
            <a href="/fragrance_explorer" target="_self" class="launch-btn">
                <div class="lb-icon">🔍</div>
                <div class="lb-title">Fragrance Explorer</div>
                <div class="lb-desc">
                    Explore perfumes by brand — click a data point to open its Fragrantica page.
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

    st.markdown('<div class="btn-row-gap"></div>', unsafe_allow_html=True)

    col_c, col_d = st.columns(2, gap="large")
    with col_c:
        st.markdown(
            f"""
            <a href="/fragrance_category" target="_self" class="launch-btn variant-c">
                <div class="lb-icon">{wheel_icon_tag}</div>
                <div class="lb-title">Fragrance Wheel Explorer</div>
                <div class="lb-desc">
                    Discover the fragrance wheel and explore fragrance families and categories.
                </div>
                <div class="lb-arrow">Open Categories →</div>
            </a>
            """,
            unsafe_allow_html=True,
        )
    with col_d:
        st.markdown(
            f"""
            <a href="/fragrance_shelf" target="_self" class="launch-btn variant-d">
                <div class="lb-icon">{shelf_icon_tag}</div>
                <div class="lb-title">Your Fragrance Shelf</div>
                <div class="lb-desc">
                    Save your own fragrances to get personalized recommendations.
                </div>
                <div class="lb-arrow">Open Gender View →</div>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Sidebar ─────────────────────────────────────────────────────
    with st.sidebar:
        st.caption("An independent data exploration concept powered by Fragrantica.")


if __name__ == "__main__":
    main()

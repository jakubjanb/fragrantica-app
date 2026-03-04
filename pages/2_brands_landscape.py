"""
Subpage: Brands Landscape

Interactive scatter-plot explorer showing every brand in the dataset
plotted by Weighted Rating (x) vs Total Votes (y, log-scale).
Marker size encodes total votes via a power-transformed scale.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
import streamlit as st
import streamlit.components.v1 as components

# ────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────
_CFG = {
    "highlight_color": "#ef4444",
    "highlight_border": "#dc2626",
    "top_tier_threshold": 4.15,
    "plot_height": 680,
    # Size-scaling
    "size_min": 6,
    "size_max": 70,
    "size_power": 0.45,
}


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────
def _prepare_brand_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-brand metrics from the raw fragrance-level data.

    Expected columns in *raw_df*: brand, rating, votes (or total_votes),
    and optionally consistency / number-of-fragrances columns.
    Adjust the column-name mapping below if your CSV differs.
    """
    # ------------------------------------------------------------------
    # 1.  Normalise column names coming from various CSV flavours
    # ------------------------------------------------------------------
    col_map: dict[str, str] = {}
    cols_lower = {c.lower(): c for c in raw_df.columns}

    # rating
    for candidate in ("weighted_rating", "weightedrating", "rating"):
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "Weighted_Rating"
            break

    # votes
    for candidate in ("total_votes", "totalvotes", "votes"):
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "total_votes"
            break

    # consistency
    for candidate in ("consistency_score", "consistencyscore", "consistency"):
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "Consistency_Score"
            break

    # total fragrances (may be pre-aggregated)
    for candidate in ("total_fragrances", "totalfragrances"):
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "total_fragrances"
            break

    # brand
    for candidate in ("brand",):
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "brand"
            break

    df = raw_df.rename(columns=col_map)

    # ------------------------------------------------------------------
    # 2.  If the data is fragrance-level, aggregate to brand-level
    # ------------------------------------------------------------------
    needed = {"brand", "Weighted_Rating", "total_votes"}
    if not needed.issubset(df.columns):
        # Attempt a lightweight aggregation from fragrance-level data
        if "brand" in df.columns and "rating" in [c.lower() for c in df.columns]:
            rating_col = [c for c in df.columns if c.lower() == "rating"][0]
            votes_col = next(
                (c for c in df.columns if c.lower() in ("votes", "total_votes")),
                None,
            )
            agg: dict = {rating_col: "mean"}
            if votes_col:
                agg[votes_col] = "sum"
            brand_df = (
                df.groupby("brand")
                .agg(**{
                    "Weighted_Rating": pd.NamedAgg(column=rating_col, aggfunc="mean"),
                    **(
                        {"total_votes": pd.NamedAgg(column=votes_col, aggfunc="sum")}
                        if votes_col
                        else {}
                    ),
                    "total_fragrances": pd.NamedAgg(column=rating_col, aggfunc="count"),
                })
                .reset_index()
            )
            if "total_votes" not in brand_df.columns:
                brand_df["total_votes"] = brand_df["total_fragrances"]
            df = brand_df

    # ------------------------------------------------------------------
    # 3.  Fill optional columns with sensible defaults
    # ------------------------------------------------------------------
    if "Consistency_Score" not in df.columns:
        df["Consistency_Score"] = 0.0
    if "total_fragrances" not in df.columns:
        df["total_fragrances"] = 1

    for col in ("Weighted_Rating", "total_votes", "Consistency_Score", "total_fragrances"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Weighted_Rating", "total_votes"])
    df = df[df["total_votes"] > 0]

    # ------------------------------------------------------------------
    # 4.  Power-transformed marker sizes
    # ------------------------------------------------------------------
    votes = df["total_votes"].values.astype(float)
    v_min, v_max = votes.min(), votes.max()
    if v_max == v_min:
        normalised = np.zeros_like(votes)
    else:
        normalised = (votes - v_min) / (v_max - v_min)
    transformed = np.power(normalised, _CFG["size_power"])
    df["_marker_size"] = _CFG["size_min"] + transformed * (
        _CFG["size_max"] - _CFG["size_min"]
    )

    return df.reset_index(drop=True)


def _build_figure(df: pd.DataFrame, highlight_brand: str | None = None) -> go.Figure:
    """Return a fully configured Plotly Figure."""

    market_avg = df["Weighted_Rating"].mean()
    x = df["Weighted_Rating"]
    y = df["total_votes"]
    sizes = df["_marker_size"].tolist()
    rating_min = float(x.min())
    rating_max = float(x.max())

    def _rating_to_viridis_color(rating: float) -> str:
        if rating_max == rating_min:
            t = 0.5
        else:
            t = max(0.0, min(1.0, (float(rating) - rating_min) / (rating_max - rating_min)))
        return sample_colorscale("Viridis", [t])[0]

    def _hover_text_color(bg_color: str) -> str:
        if bg_color.startswith("#"):
            hex_color = bg_color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join(ch * 2 for ch in hex_color)
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        elif bg_color.startswith("rgb"):
            rgb = bg_color[bg_color.find("(") + 1 : bg_color.find(")")].split(",")
            r, g, b = (int(float(c.strip())) for c in rgb[:3])
        else:
            return "#111827"
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#111827" if luminance > 165 else "#f9fafb"

    # --- colours / opacities depending on highlight state ---
    if highlight_brand:
        mask = df["brand"].str.lower() == highlight_brand.lower()
        colors = [
            _CFG["highlight_color"] if m else val
            for m, val in zip(mask, df["Weighted_Rating"])
        ]
        opacities = [1.0 if m else 0.55 for m in mask]
        line_widths = [3 if m else 0.5 for m in mask]
        line_colors = [
            _CFG["highlight_border"] if m else "rgba(255,255,255,0.5)"
            for m in mask
        ]
        sizes = [
            max(s * 1.35, 20) if m else s for m, s in zip(mask, sizes)
        ]
        hover_bgcolors = [
            _CFG["highlight_color"] if m else _rating_to_viridis_color(val)
            for m, val in zip(mask, df["Weighted_Rating"])
        ]
    else:
        colors = df["Weighted_Rating"].tolist()
        opacities = [0.82] * len(df)
        line_widths = [0.8] * len(df)
        line_colors = ["rgba(255,255,255,0.55)"] * len(df)
        hover_bgcolors = [_rating_to_viridis_color(val) for val in df["Weighted_Rating"]]
    hover_font_colors = [_hover_text_color(c) for c in hover_bgcolors]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            text=df["brand"],
            customdata=np.stack(
                [
                    df["Consistency_Score"],
                    df["total_fragrances"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Weighted Rating: %{x:.2f}<br>"
                "Total Votes: %{y:,.0f}<br>"
                "Consistency: %{customdata[0]:.1f}%<br>"
                "Portfolio: %{customdata[1]:.0f} fragrances"
                "<extra></extra>"
            ),
            marker=dict(
                size=sizes,
                color=colors,
                colorscale="Viridis",
                showscale=not bool(highlight_brand),
                colorbar=dict(
                    title=dict(text="Rating", font=dict(size=13)),
                    thickness=14,
                    len=0.75,
                    y=0.5,
                    tickfont=dict(size=11),
                    outlinewidth=0,
                    xpad=10,
                ),
                line=dict(width=line_widths, color=line_colors),
                opacity=opacities,
            ),
            hoverlabel=dict(
                bgcolor=hover_bgcolors,
                bordercolor=hover_bgcolors,
                font=dict(color=hover_font_colors),
            ),
        )
    )

    x_min = float(x.min()) - 0.02
    x_max = float(x.max()) + 0.02

    # --- layout ---
    fig.update_layout(
        title=dict(
            text="Brand Landscape: Quality vs. Popularity",
            font=dict(size=20),
            x=0.02,
            xanchor="left",
        ),
        xaxis=dict(
            title="Weighted Rating",
            tickformat=".2f",
            gridcolor="rgba(0,0,0,0.06)",
            zeroline=False,
            range=[x_min, x_max],
        ),
        yaxis=dict(
            title="Total Votes (Log Scale)",
            type="log",
            range=[np.log10(max(float(y.min()), 1)) - 0.3, np.log10(float(y.max())) + 0.3],
            gridcolor="rgba(0,0,0,0.06)",
            zeroline=False,
        ),
        hovermode="closest",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=70, r=40, t=60, b=60),
        height=_CFG["plot_height"],
    )

    # Top-tier shaded region
    fig.add_shape(
        type="rect",
        x0=_CFG["top_tier_threshold"],
        x1=x_max,
        y0=0,
        y1=1,
        yref="paper",
        fillcolor="rgba(16, 185, 129, 0.06)",
        line_width=0,
    )

    # Market-average dashed line
    fig.add_shape(
        type="line",
        x0=market_avg,
        x1=market_avg,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="rgba(107,114,128,0.5)", dash="dash", width=1.5),
    )

    fig.add_annotation(
        x=_CFG["top_tier_threshold"] + 0.005,
        y=1,
        xref="x",
        yref="paper",
        text=f"Top Tier (>{_CFG['top_tier_threshold']})",
        showarrow=False,
        font=dict(size=11, color="#059669"),
        xanchor="left",
        yanchor="top",
        yshift=-8,
    )
    fig.add_annotation(
        x=market_avg,
        y=1,
        xref="x",
        yref="paper",
        text=f"Avg: {market_avg:.2f}",
        showarrow=False,
        font=dict(size=10, color="#6b7280"),
        xanchor="left",
        xshift=5,
        yanchor="top",
        yshift=-8,
    )

    # Highlight annotation arrow
    if highlight_brand:
        row = df[df["brand"].str.lower() == highlight_brand.lower()]
        if not row.empty:
            r = row.iloc[0]
            fig.add_annotation(
                x=r["Weighted_Rating"],
                y=r["total_votes"],
                text=f"<b>{r['brand']}</b>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=_CFG["highlight_color"],
                ax=55,
                ay=-45,
                bgcolor="white",
                bordercolor=_CFG["highlight_color"],
                borderwidth=2,
                borderpad=6,
                font=dict(size=13, color=_CFG["highlight_border"]),
            )

    return fig


def _percentile_color(t: float) -> str:
    """Return an RGB string along a 5-stop professional gradient."""
    stops = [
        (0.00, 203, 213, 225),
        (0.25, 94, 200, 200),
        (0.50, 16, 185, 129),
        (0.75, 99, 102, 241),
        (1.00, 124, 58, 237),
    ]
    i = 0
    for i in range(len(stops) - 2):
        if t <= stops[i + 1][0]:
            break
    a, b = stops[i], stops[i + 1]
    f = (t - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
    r = int(a[1] + f * (b[1] - a[1]))
    g = int(a[2] + f * (b[2] - a[2]))
    bl = int(a[3] + f * (b[3] - a[3]))
    return f"rgb({r},{g},{bl})"


def _metric_card(label: str, value: str, percentile: float, col) -> None:
    """Render a colour-coded metric inside a Streamlit column."""
    color = _percentile_color(percentile)
    pct_label = f"P{int(percentile * 100)}"
    col.markdown(
        f"""
        <div style="
            background: {color.replace('rgb', 'rgba').replace(')', ',0.08)')};
            border-radius: 12px; padding: 18px 12px; text-align: center;
        ">
            <div style="font-size:26px; font-weight:700; color:{color};">{value}</div>
            <div style="font-size:12px; color:#6b7280; text-transform:uppercase;
                        letter-spacing:0.5px; margin-top:4px;">{label}</div>
            <span style="display:inline-block; margin-top:6px; padding:2px 8px;
                         border-radius:10px; font-size:11px; font-weight:600;
                         background:{color.replace('rgb','rgba').replace(')',',0.14)')};
                         color:{color};">{pct_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ────────────────────────────────────────────────────────────
# MAIN PAGE
# ────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="Brands Landscape",
        page_icon="🗺️️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🗺️ Brand Landscape Explorer")
    st.markdown(
        '<p class="subtitle">Compare all brands by quality and popularity. Discover key statistics for any brand.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .subtitle {
            color: #6b7280;
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
        div[data-testid="stToggle"] label p {
            font-weight: 600;
            color: #111827;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Load data ────────────────────────────────────────────
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "Data" / "all_brands.csv"

    if not csv_path.exists():
        st.error(f"Data file not found: `{csv_path}`")
        st.stop()

    # Load pre-aggregated brand data directly
    raw_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    if raw_df.empty:
        st.warning("No data available after cleaning.")
        st.stop()

    df = _prepare_brand_df(raw_df)
    if df.empty:
        st.warning("Could not compute brand-level metrics.")
        st.stop()

    brands_list = sorted(df["brand"].unique().tolist())

    # ── Search & highlight controls ──────────────────────────
    # Search bar width: 50% shorter (4 -> 2); reset button width: 30% narrower (1 -> 0.7)
    col_search, col_btn, _ = st.columns([2, 0.7, 2.3], vertical_alignment="bottom")
    with col_search:
        selected_brand = st.selectbox(
            "🔍 Search & highlight a brand",
            options=[""] + brands_list,
            index=0,
            help="Select a brand to highlight it on the scatter plot.",
        )
    with col_btn:
        reset = st.button("↺ Reset", use_container_width=True)

    highlight = selected_brand if selected_brand and not reset else None

    # ── Info card for highlighted brand ──────────────────────
    if highlight:
        row = df[df["brand"].str.lower() == highlight.lower()]
        if not row.empty:
            b = row.iloc[0]
            st.markdown(f"### 🎯 {b['brand']}")

            # Compute percentile ranks (0-1)
            def _pct(val, col):
                lo, hi = df[col].min(), df[col].max()
                return 0.5 if hi == lo else max(0, min(1, (val - lo) / (hi - lo)))

            mc1, mc2, mc3, mc4 = st.columns(4)
            _metric_card(
                "Fragrances",
                str(int(b["total_fragrances"])),
                _pct(b["total_fragrances"], "total_fragrances"),
                mc1,
            )
            _metric_card(
                "Total Votes",
                f"{int(b['total_votes']):,}",
                _pct(b["total_votes"], "total_votes"),
                mc2,
            )
            _metric_card(
                "Weighted Rating",
                f"{b['Weighted_Rating']:.2f}",
                _pct(b["Weighted_Rating"], "Weighted_Rating"),
                mc3,
            )
            _metric_card(
                "Consistency",
                f"{b['Consistency_Score']:.1f}%",
                _pct(b["Consistency_Score"], "Consistency_Score"),
                mc4,
            )
            st.divider()

    # ── Vote threshold filter (30th percentile) ────────────
    if "brands_show_all" not in st.session_state:
        st.session_state.brands_show_all = False

    st.toggle("👁 Show all brands", key="brands_show_all")

    vote_threshold = df["total_votes"].quantile(0.30)
    total_brands = len(df)

    if not st.session_state.brands_show_all:
        df_plot = df[df["total_votes"] >= vote_threshold].copy()
        shown = len(df_plot)
        st.caption(f"Showing {shown} of {total_brands} brands (votes ≥ {vote_threshold:,.0f})")
    else:
        df_plot = df
        st.caption(f"Showing all {total_brands} brands")

    # ── Plotly chart ─────────────────────────────────────────
    fig = _build_figure(df_plot, highlight_brand=highlight)
    st.plotly_chart(fig, use_container_width=True)


    # ── Expandable data table ────────────────────────────────
    display_df = (
        df[["brand", "Weighted_Rating", "total_votes", "Consistency_Score", "total_fragrances"]]
        .sort_values("Weighted_Rating", ascending=False)
        .reset_index(drop=True)
    )
    display_df.columns = ["Brand", "Weighted Rating", "Total Votes", "Consistency %", "Fragrances"]

    with st.expander(f"📊 Brand data table ({len(display_df)} brands)"):
        bar_cols = {
            "Weighted Rating": "{:.3f}",
            "Total Votes": "{:,.0f}",
            "Consistency %": "{:.1f}%",
            "Fragrances": "{:d}",
        }
        col_ranges = {
            col: (float(display_df[col].min()), float(display_df[col].max()))
            for col in bar_cols
        }

        def _bar_cell(val: float, col_min: float, col_max: float, fmt: str) -> str:
            t = 0.5 if col_max == col_min else max(0.0, min(1.0, (val - col_min) / (col_max - col_min)))
            color = _percentile_color(t)
            bar_color = color.replace("rgb", "rgba").replace(")", ",0.22)")
            width_pct = max(t * 100, 2)
            formatted = fmt.format(val)
            return (
                f'<div style="position:relative; height:28px; line-height:28px;">'
                f'<div style="position:absolute; top:2px; bottom:2px; left:0;'
                f' width:{width_pct:.1f}%; background:{bar_color};'
                f' border-radius:4px;"></div>'
                f'<span style="position:relative; z-index:1; padding-left:6px;'
                f' font-size:13px; color:#1a1a1a;">{formatted}</span>'
                f'</div>'
            )

        # Build HTML table
        header = "".join(
            f'<th style="text-align:left; padding:10px 12px; font-size:13px;'
            f' color:#6b7280; border-bottom:2px solid #e5e7eb;'
            f' text-transform:uppercase; letter-spacing:0.5px;'
            f' cursor:pointer; user-select:none;"'
            f' data-col-idx="{i}">{c} <span class="sort-arrow" style="font-size:10px;"></span></th>'
            for i, c in enumerate(display_df.columns)
        )
        rows_html = []
        for _, row in display_df.iterrows():
            cells = []
            for col in display_df.columns:
                val = row[col]
                if col in bar_cols:
                    cmin, cmax = col_ranges[col]
                    cell_content = _bar_cell(val, cmin, cmax, bar_cols[col])
                else:
                    cell_content = f'<span style="font-size:13px; color:#1a1a1a;">{val}</span>'
                cells.append(
                    f'<td style="padding:4px 12px; border-bottom:1px solid #f0f0f0;">'
                    f'{cell_content}</td>'
                )
            rows_html.append(f'<tr>{"".join(cells)}</tr>')

        sort_js = """
        <script>
        (function() {
            const table = document.getElementById('brand-table');
            if (!table) return;
            const headers = table.querySelectorAll('thead th');
            let sortCol = -1, sortAsc = true;

            headers.forEach(function(th) {
                th.addEventListener('click', function() {
                    const idx = parseInt(th.getAttribute('data-col-idx'));
                    if (sortCol === idx) { sortAsc = !sortAsc; }
                    else { sortCol = idx; sortAsc = true; }

                    // Update arrows
                    headers.forEach(function(h) {
                        h.querySelector('.sort-arrow').textContent = '';
                    });
                    th.querySelector('.sort-arrow').textContent = sortAsc ? ' ▲' : ' ▼';

                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const isNumeric = idx > 0;

                    rows.sort(function(a, b) {
                        let aText = a.children[idx].textContent.trim();
                        let bText = b.children[idx].textContent.trim();
                        if (isNumeric) {
                            let aVal = parseFloat(aText.replace(/[,%]/g, ''));
                            let bVal = parseFloat(bText.replace(/[,%]/g, ''));
                            return sortAsc ? aVal - bVal : bVal - aVal;
                        } else {
                            return sortAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
                        }
                    });
                    rows.forEach(function(r) { tbody.appendChild(r); });
                });
            });
        })();
        </script>
        """

        html = (
            f'<div style="max-height:500px; overflow-y:auto; border:1px solid #e5e7eb;'
            f' border-radius:8px;">'
            f'<table id="brand-table" style="width:100%; border-collapse:collapse; font-family:sans-serif;">'
            f'<thead style="position:sticky; top:0; background:white; z-index:2;">'
            f'<tr>{header}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody>'
            f'</table></div>{sort_js}'
        )
        components.html(html, height=520, scrolling=False)


if __name__ == "__main__":
    main()

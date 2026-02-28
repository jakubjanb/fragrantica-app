"""UI section for fragrance wheel coverage visualization."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.shelf.constants import FAMILY_COLORS, WHEEL_FAMILY_ORDER
from src.shelf.domain import _build_sunburst_data, coverage_stats


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return (30, 41, 59)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return (30, 41, 59)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _darken_hex(hex_color: str, factor: float = 0.28) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((int(r * (1.0 - factor)), int(g * (1.0 - factor)), int(b * (1.0 - factor))))


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def _to_linear(channel: int) -> float:
        c = channel / 255.0
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * _to_linear(r) + 0.7152 * _to_linear(g) + 0.0722 * _to_linear(b)


def _contrast_ratio(l1: float, l2: float) -> float:
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _best_contrast_text(bg_hex: str) -> str:
    bg_lum = _relative_luminance(_hex_to_rgb(bg_hex))
    white_lum = _relative_luminance((255, 255, 255))
    black_lum = _relative_luminance((0, 0, 0))
    white_ratio = _contrast_ratio(bg_lum, white_lum)
    black_ratio = _contrast_ratio(bg_lum, black_lum)
    return "#ffffff" if white_ratio >= black_ratio else "#111827"


def _render_coverage(df_shelf_enriched: pd.DataFrame) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Install plotly (`pip install plotly`) to view the fragrance wheel.")
        return

    st.subheader("Fragrance wheel coverage")
    st.markdown(
        '<p class="section-note">See how broadly your shelf covers fragrance families and categories.</p>',
        unsafe_allow_html=True,
    )
    stats = coverage_stats(df_shelf_enriched)

    metric_cards = [
        ("Coverage", f"{stats['coverage_pct']:.1f}%"),
        ("Covered families", f"{stats['covered_families']} / {stats['total_families']}"),
        ("Category coverage", f"{stats['category_coverage_pct']:.1f}%"),
        ("Covered categories", f"{stats['covered_categories']} / {stats['total_categories']}"),
    ]
    cards_html = "".join(
        (
            '<div class="coverage-stat-card">'
            f'<p class="coverage-stat-label">{label}</p>'
            f'<p class="coverage-stat-value">{value}</p>'
            "</div>"
        )
        for label, value in metric_cards
    )
    st.markdown(f'<div class="coverage-stat-row">{cards_html}</div>', unsafe_allow_html=True)

    data = _build_sunburst_data(df_shelf_enriched)
    total = data["total_items"]
    hover_bg_colors: list[str] = []
    hover_border_colors: list[str] = []
    hover_font_colors: list[str] = []

    for seg_color, cd in zip(data["colors"], data["customdata"]):
        if cd.get("is_empty"):
            bg_color = "#6b7280"
            border_color = "#4b5563"
        else:
            bg_color = _darken_hex(str(seg_color), 0.28)
            border_color = _darken_hex(str(seg_color), 0.42)

        hover_bg_colors.append(bg_color)
        hover_border_colors.append(border_color)
        hover_font_colors.append(_best_contrast_text(bg_color))

    hover_texts: list[str] = []
    for cd in data["customdata"]:
        if cd.get("is_empty"):
            hover_texts.append(f"<b>{cd['family']}</b><br>Not on your shelf")
        elif "subcat" in cd:
            pct = 100.0 * cd["count"] / cd["total"] if cd["total"] else 0.0
            hover_texts.append(
                f"<b>{cd['family']}</b> › {cd['subcat']}"
                f"<br>{cd['count']} fragrance{'s' if cd['count'] != 1 else ''} · {pct:.1f}%"
            )
        else:
            pct = 100.0 * cd["count"] / cd["total"] if cd["total"] else 0.0
            hover_texts.append(
                f"<b>{cd['family']}</b>"
                f"<br>{cd['count']} fragrance{'s' if cd['count'] != 1 else ''} · {pct:.1f}%"
            )

    fig = go.Figure(
        go.Sunburst(
            ids=data["ids"],
            labels=data["labels"],
            parents=data["parents"],
            values=data["values"],
            branchvalues="total",
            marker=dict(
                colors=data["colors"],
                line=dict(color="#ffffff", width=1.5),
            ),
            hovertext=hover_texts,
            hoverinfo="text",
            textfont=dict(size=12, family="sans-serif"),
            insidetextorientation="radial",
            maxdepth=2,
            hoverlabel=dict(
                bgcolor=hover_bg_colors,
                bordercolor=hover_border_colors,
                font=dict(color=hover_font_colors, size=13),
            ),
        )
    )

    annotations: list[dict[str, Any]] = []
    if total == 0:
        annotations.append(
            dict(
                text="Add fragrances<br>to see your coverage",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color="#64748b"),
            )
        )

    fig.update_layout(
        height=480,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=annotations,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption("Hover segments to explore categories. Empty (grey) segments indicate uncovered families.")

    counts_lookup: dict[str, int] = dict(
        zip(stats["family_counts"]["family"], stats["family_counts"]["count"])
    )
    covered = [f for f in WHEEL_FAMILY_ORDER if counts_lookup.get(f, 0) > 0]
    if covered:
        swatches = "".join(
            f'<span style="display:inline-flex;align-items:center;gap:5px;'
            f'margin:0 12px 6px 0;">'
            f'<span style="display:inline-block;width:11px;height:11px;border-radius:50%;'
            f'background:{FAMILY_COLORS[f]};flex-shrink:0;"></span>'
            f'<span style="font-size:0.82rem;color:#334155;">'
            f'{f} <span style="color:#94a3b8;">({counts_lookup[f]})</span>'
            f'</span></span>'
            for f in covered
        )
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;padding:2px 0 8px;">{swatches}</div>',
            unsafe_allow_html=True,
        )

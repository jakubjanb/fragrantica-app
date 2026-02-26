"""UI section for fragrance wheel coverage visualization."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.shelf.constants import FAMILY_COLORS, FAMILY_ORDER
from src.shelf.domain import _build_sunburst_data, coverage_stats


def _render_coverage(df_shelf_enriched: pd.DataFrame) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Install plotly (`pip install plotly`) to view the fragrance wheel.")
        return

    st.subheader("Fragrance wheel coverage")
    st.markdown(
        '<p class="section-note">See how broadly your shelf covers fragrance families.</p>',
        unsafe_allow_html=True,
    )
    stats = coverage_stats(df_shelf_enriched)

    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Coverage", f"{stats['coverage_pct']:.1f}%")
    metric_col2.metric(
        "Covered families",
        f"{stats['covered_families']} / {stats['total_families']}",
    )

    data = _build_sunburst_data(df_shelf_enriched)
    total = data["total_items"]

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
                bgcolor="#1e293b",
                bordercolor="#1e293b",
                font=dict(color="#f8fafc", size=13),
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
    st.caption("Hover segments to explore subcategories. Empty (grey) segments indicate uncovered families.")

    counts_lookup: dict[str, int] = dict(
        zip(stats["family_counts"]["family"], stats["family_counts"]["count"])
    )
    covered = [f for f in FAMILY_ORDER if counts_lookup.get(f, 0) > 0]
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

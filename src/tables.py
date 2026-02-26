"""Shared table rendering utilities for fragrance pages."""

from __future__ import annotations

from html import escape

import streamlit as st


def _percentile_color(t: float) -> str:
    """Return an RGB string along a 5-stop gradient used across analytics tables."""
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


def _bar_cell(
    val: float,
    col_min: float,
    col_max: float,
    fmt: str,
    *,
    height_px: int = 28,
) -> str:
    """Return HTML for a value-over-bar cell used in Top-10 style tables."""
    t = 0.5 if col_max == col_min else max(0.0, min(1.0, (val - col_min) / (col_max - col_min)))
    color = _percentile_color(t)
    bar_color = color.replace("rgb", "rgba").replace(")", ",0.22)")
    width_pct = max(t * 100, 2)
    formatted = escape(fmt.format(val))
    return (
        f'<div style="position:relative; height:{height_px}px; line-height:{height_px}px;">'
        f'<div style="position:absolute; top:2px; bottom:2px; left:0;'
        f' width:{width_pct:.1f}%; background:{bar_color};'
        f' border-radius:4px;"></div>'
        f'<span style="position:relative; z-index:1; padding-left:6px;'
        f' font-size:13px; color:#1a1a1a;">{formatted}</span>'
        f'</div>'
    )


def render_top_fragrances_table(display_df) -> None:
    """Render a styled Top-10 table with the same visual language as Brand data table."""
    if display_df.empty:
        st.info("No fragrances meet the current ranking criteria.")
        return

    bar_cols = {
        "Rating": "{:.3f}",
        "Votes": "{:,.0f}",
    }
    col_ranges = {
        col: (float(display_df[col].min()), float(display_df[col].max()))
        for col in bar_cols
    }

    header = "".join(
        f'<th style="text-align:left; padding:10px 12px; font-size:13px;'
        f' color:#6b7280; border-bottom:2px solid #e5e7eb;'
        f' text-transform:uppercase; letter-spacing:0.5px;">{c}</th>'
        for c in display_df.columns
    )

    rows_html = []
    for _, row in display_df.iterrows():
        cells = []
        for col in display_df.columns:
            val = row[col]
            if col in bar_cols:
                cmin, cmax = col_ranges[col]
                cell_content = _bar_cell(float(val), cmin, cmax, bar_cols[col])
            elif col == "Link":
                link = "" if val is None else str(val).strip()
                if link and link.lower() != "nan":
                    safe_link = escape(link, quote=True)
                    cell_content = (
                        f'<a href="{safe_link}" target="_blank" rel="noopener noreferrer" '
                        f'style="font-size:13px; color:#2563eb; text-decoration:none;">Open</a>'
                    )
                else:
                    cell_content = '<span style="font-size:13px; color:#9ca3af;">-</span>'
            else:
                text_val = "-" if val is None or str(val).lower() == "nan" else str(val)
                cell_content = f'<span style="font-size:13px; color:#1a1a1a;">{escape(text_val)}</span>'

            cells.append(
                f'<td style="padding:4px 12px; border-bottom:1px solid #f0f0f0;">'
                f'{cell_content}</td>'
            )
        rows_html.append(f'<tr>{"".join(cells)}</tr>')

    table_height = min(500, max(220, 96 + len(display_df) * 38))
    html = (
        f'<div style="max-height:{table_height}px; overflow-y:auto; border:1px solid #e5e7eb;'
        f' border-radius:8px;">'
        f'<table style="width:100%; border-collapse:collapse; font-family:sans-serif;">'
        f'<thead style="position:sticky; top:0; background:white; z-index:2;">'
        f'<tr>{header}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        f'</table></div>'
    )
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)

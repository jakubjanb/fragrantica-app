"""
Subpage: Fragrance Categories

Visualize fragrance families and categories using a two-level sunburst chart.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.sunburst_component import render_sunburst_click
from src.tables import render_top_fragrances_table

MASTER_CSV = Path(__file__).resolve().parent.parent / "Data" / "all_brands_clean.csv"

FAMILY_COLORS: dict[str, str] = {
    "Floral": "#e75480",
    "Oriental": "#9b59b6",
    "Woody": "#a0522d",
    "Aromatic": "#27ae60",
    "Chypre": "#1abc9c",
    "Citrus": "#f39c12",
    "Leather": "#795548",
    "Other": "#90a4ae",
}

FAMILIES = ["Floral", "Oriental", "Woody", "Aromatic", "Chypre", "Citrus", "Leather"]
SEX_BUCKETS = ("women", "unisex", "men")
SEX_BUTTON_KEYS: dict[str, str] = {
    "women": "fc_women_filter",
    "unisex": "fc_unisex_filter",
    "men": "fc_men_filter",
}


@st.cache_data(show_spinner=False)
def _load_raw_data(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path, encoding="utf-8-sig")


def _get_family(label: str) -> str:
    label_l = label.lower()
    for family in FAMILIES:
        if label_l.startswith(family.lower()):
            return family
    return "Other"


def _mix_hex(hex_a: str, hex_b: str, t: float) -> str:
    t = max(0.0, min(1.0, float(t)))
    a = hex_a.lstrip("#")
    b = hex_b.lstrip("#")
    ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    bch = int(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bch:02x}"


def _family_colorscale(family: str) -> list[tuple[float, str]]:
    base = FAMILY_COLORS.get(family, FAMILY_COLORS["Other"])
    return [
        (0.00, _mix_hex(base, "#ffffff", 0.72)),
        (0.35, _mix_hex(base, "#ffffff", 0.40)),
        (0.70, _mix_hex(base, "#111827", 0.15)),
        (1.00, _mix_hex(base, "#111827", 0.34)),
    ]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    color = str(hex_color or "").strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        return (100, 116, 139)
    try:
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    except ValueError:
        return (100, 116, 139)


def _sample_colorscale_hex(colorscale: list[tuple[float, str]], value: float) -> str:
    if not colorscale:
        return "#64748b"

    point = max(0.0, min(1.0, float(value)))
    ordered = sorted(colorscale, key=lambda row: float(row[0]))

    if point <= float(ordered[0][0]):
        return ordered[0][1]

    for idx in range(1, len(ordered)):
        left_stop, left_hex = float(ordered[idx - 1][0]), str(ordered[idx - 1][1])
        right_stop, right_hex = float(ordered[idx][0]), str(ordered[idx][1])
        if point <= right_stop:
            span = right_stop - left_stop
            t = 0.0 if span <= 0 else (point - left_stop) / span
            return _mix_hex(left_hex, right_hex, t)

    return str(ordered[-1][1])


def _relative_luminance(hex_color: str) -> float:
    def _channel(v: int) -> float:
        c = v / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _text_color_for_background(hex_color: str) -> str:
    return "#0f172a" if _relative_luminance(hex_color) >= 0.35 else "#ffffff"


def _normalise_rating(value: float, min_rating: float, max_rating: float) -> float:
    if max_rating <= min_rating:
        return 0.5
    return max(0.0, min(1.0, (value - min_rating) / (max_rating - min_rating)))


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({r},{g},{b},{a:.3f})"


def _family_metric_card(label: str, value: str, percentile: float, family: str, col) -> None:
    pct = max(0.0, min(1.0, float(percentile)))
    # Keep accents in the readable range of the family palette.
    accent_position = 0.24 + (0.70 * pct)
    accent = _sample_colorscale_hex(_family_colorscale(family), accent_position)
    text_accent = _mix_hex(accent, "#111827", 0.20)

    col.markdown(
        f"""
        <div style="
            background: {_hex_to_rgba(accent, 0.10)};
            border: 1px solid {_hex_to_rgba(accent, 0.24)};
            border-radius: 12px;
            padding: 18px 12px;
            text-align: center;
        ">
            <div style="font-size:26px; font-weight:700; color:{text_accent};">{value}</div>
            <div style="font-size:12px; color:#6b7280; text-transform:uppercase;
                        letter-spacing:0.5px; margin-top:4px;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_sex_button_palette(df_plot: pd.DataFrame, family: str) -> dict[str, dict[str, str]]:
    fallback_base = "#64748b"
    palette: dict[str, dict[str, str]] = {}
    colorscale = _family_colorscale(family)

    rating_series = (
        pd.to_numeric(df_plot["rating"], errors="coerce")
        if "rating" in df_plot.columns
        else pd.Series(dtype="float64")
    )
    valid_ratings = rating_series.dropna()
    min_rating = float(valid_ratings.min()) if not valid_ratings.empty else 0.0
    max_rating = float(valid_ratings.max()) if not valid_ratings.empty else 5.0

    for bucket in SEX_BUCKETS:
        if "sex" in df_plot.columns:
            bucket_ratings = pd.to_numeric(
                df_plot.loc[df_plot["sex"].eq(bucket), "rating"],
                errors="coerce",
            ).dropna()
        else:
            bucket_ratings = pd.Series(dtype="float64")

        if bucket_ratings.empty or valid_ratings.empty:
            active_bg = fallback_base
        else:
            representative_rating = float(bucket_ratings.median())
            normalized = _normalise_rating(representative_rating, min_rating, max_rating)
            active_bg = _sample_colorscale_hex(colorscale, normalized)

        inactive_bg = _mix_hex(active_bg, "#ffffff", 0.72)
        active_border = _mix_hex(active_bg, "#111827", 0.08)
        inactive_border = _mix_hex(inactive_bg, "#111827", 0.15)

        palette[bucket] = {
            "active_bg": active_bg,
            "active_hover_bg": _mix_hex(active_bg, "#111827", 0.12),
            "active_border": active_border,
            "active_text": _text_color_for_background(active_bg),
            "inactive_bg": inactive_bg,
            "inactive_hover_bg": _mix_hex(inactive_bg, "#111827", 0.08),
            "inactive_border": inactive_border,
            "inactive_text": _text_color_for_background(inactive_bg),
            "disabled_bg": "#f1f5f9",
            "disabled_border": "#cbd5e1",
            "disabled_text": "#94a3b8",
        }

    return palette


def _render_sex_button_palette_css(button_palette: dict[str, dict[str, str]]) -> None:
    css_rules: list[str] = []

    for bucket, key in SEX_BUTTON_KEYS.items():
        style = button_palette.get(bucket)
        if not style:
            continue

        key_variants = [key, key.replace("_", "-")]
        base_selectors = list(dict.fromkeys(f".st-key-{variant} button" for variant in key_variants))
        base_selector = ", ".join(base_selectors)
        hover_selector = ", ".join(f"{selector}:hover" for selector in base_selectors)
        primary_selector = ", ".join(f'{selector}[kind="primary"]' for selector in base_selectors)
        primary_hover_selector = ", ".join(
            f'{selector}[kind="primary"]:hover' for selector in base_selectors
        )
        disabled_selector = ", ".join(f"{selector}:disabled" for selector in base_selectors)
        css_rules.append(
            f"""
            {base_selector} {{
                background: {style["inactive_bg"]} !important;
                border-color: {style["inactive_border"]} !important;
                color: {style["inactive_text"]} !important;
            }}
            {hover_selector} {{
                background: {style["inactive_hover_bg"]} !important;
                border-color: {style["inactive_border"]} !important;
                color: {style["inactive_text"]} !important;
            }}
            {primary_selector} {{
                background: {style["active_bg"]} !important;
                border-color: {style["active_border"]} !important;
                color: {style["active_text"]} !important;
            }}
            {primary_hover_selector} {{
                background: {style["active_hover_bg"]} !important;
                border-color: {style["active_border"]} !important;
                color: {style["active_text"]} !important;
            }}
            {disabled_selector} {{
                background: {style["disabled_bg"]} !important;
                border-color: {style["disabled_border"]} !important;
                color: {style["disabled_text"]} !important;
                opacity: 1 !important;
            }}
            """
        )

    if css_rules:
        st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)


def _lighten_hex_color(hex_color: str, offset: int = 45) -> str:
    base = hex_color.lstrip("#")
    r, g, b = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
    return f"#{min(r + offset, 255):02x}{min(g + offset, 255):02x}{min(b + offset, 255):02x}"


def _build_category_counts(df_raw: pd.DataFrame) -> pd.DataFrame:
    cat_counts = (
        df_raw["fragrance_category"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s.ne("")]
        .value_counts()
        .reset_index()
    )
    cat_counts.columns = ["category", "count"]
    cat_counts["family"] = cat_counts["category"].apply(_get_family)
    return cat_counts


def _normalise_sex_bucket(value: Any) -> str:
    label = " ".join(str(value or "").strip().lower().split())
    if not label:
        return ""

    women_tokens = {"women", "woman", "female", "for women", "feminine", "ladies", "lady"}
    unisex_tokens = {"unisex", "uni sex", "uni-sex"}
    men_tokens = {"men", "man", "male", "for men", "masculine", "gentlemen", "gentleman"}

    if label in women_tokens:
        return "women"
    if label in unisex_tokens:
        return "unisex"
    if label in men_tokens:
        return "men"
    return ""


def _build_sex_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "sex" not in df.columns:
        return {bucket: 0 for bucket in SEX_BUCKETS}
    sex_series = df["sex"].fillna("").astype(str).str.strip().str.lower()
    return {bucket: int(sex_series.eq(bucket).sum()) for bucket in SEX_BUCKETS}


def _reset_sex_filters_page3() -> None:
    st.session_state.fc_sex_women = True
    st.session_state.fc_sex_unisex = True
    st.session_state.fc_sex_men = True


def _selected_page3_sexes() -> list[str]:
    selected: list[str] = []
    if st.session_state.get("fc_sex_women", False):
        selected.append("women")
    if st.session_state.get("fc_sex_unisex", False):
        selected.append("unisex")
    if st.session_state.get("fc_sex_men", False):
        selected.append("men")
    return selected


def _sync_page3_sex_filter_state(sex_counts: dict[str, int], scope_id: str) -> None:
    if st.session_state.get("fc_prev_scope") != scope_id:
        _reset_sex_filters_page3()
        st.session_state.fc_show_all = False
        st.session_state.fc_prev_scope = scope_id

    if sex_counts["women"] == 0:
        st.session_state.fc_sex_women = False
    if sex_counts["unisex"] == 0:
        st.session_state.fc_sex_unisex = False
    if sex_counts["men"] == 0:
        st.session_state.fc_sex_men = False

    if any(sex_counts.values()) and not _selected_page3_sexes():
        if sex_counts["women"] > 0:
            st.session_state.fc_sex_women = True
        elif sex_counts["unisex"] > 0:
            st.session_state.fc_sex_unisex = True
        else:
            st.session_state.fc_sex_men = True


def _prepare_family_plot_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    required_cols = {"name", "rating", "votes", "fragrance_category"}
    if not required_cols.issubset(df_raw.columns):
        return pd.DataFrame(columns=["name", "rating", "votes", "fragrance_category", "family"])

    df = df_raw.copy()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce")
    df["fragrance_category"] = df["fragrance_category"].fillna("").astype(str).str.strip()
    df = df[df["fragrance_category"] != ""].copy()
    df["family"] = df["fragrance_category"].apply(_get_family)
    df = df.dropna(subset=["name", "rating", "votes"]).copy()
    df = df[df["votes"] > 0].copy()

    if "url" not in df.columns:
        df["url"] = ""
    else:
        df["url"] = df["url"].fillna("").astype(str)

    if "brand" not in df.columns:
        df["brand"] = ""
    else:
        df["brand"] = df["brand"].fillna("").astype(str)

    if "sex" not in df.columns:
        df["sex"] = ""
    else:
        df["sex"] = df["sex"].map(_normalise_sex_bucket)

    return df


def _extract_selection_points(event_state: Any) -> list[dict[str, Any]]:
    if event_state is None:
        return []

    if isinstance(event_state, dict):
        if any(k in event_state for k in ("id", "label", "parent", "customdata", "point_number", "pointNumber")):
            return [event_state]

    if isinstance(event_state, dict):
        selection = event_state.get("selection", {})
    else:
        selection = getattr(event_state, "selection", {})

    if isinstance(selection, dict):
        points = selection.get("points", [])
    else:
        points = getattr(selection, "points", [])

    if not isinstance(points, list):
        return []
    return [p for p in points if isinstance(p, dict)]


def _parse_sunburst_point(
    point: dict[str, Any], point_lookup: dict[int, dict[str, str]]
) -> tuple[str | None, str | None]:
    node_id = str(point.get("id", "")).strip()
    label = str(point.get("label", "")).strip()
    parent = str(point.get("parent", "")).strip()

    point_number_raw = (
        point.get("point_number")
        if point.get("point_number") is not None
        else point.get("pointNumber")
    )
    if point_number_raw is None:
        point_number_raw = (
            point.get("point_index")
            if point.get("point_index") is not None
            else point.get("pointIndex")
        )

    if point_number_raw is not None:
        try:
            point_number = int(point_number_raw)
            lookup_node = point_lookup.get(point_number, {})
            node_id = node_id or str(lookup_node.get("id", "")).strip()
            label = label or str(lookup_node.get("label", "")).strip()
            parent = parent or str(lookup_node.get("parent", "")).strip()
        except (TypeError, ValueError):
            pass

    custom = point.get("customdata")
    if isinstance(custom, (list, tuple)):
        custom_family = str(custom[1]).strip() if len(custom) > 1 else ""
        custom_category = str(custom[2]).strip() if len(custom) > 2 else ""
        custom_node_type = str(custom[3]).strip().lower() if len(custom) > 3 else ""
        if custom_node_type == "family" and custom_family:
            return custom_family, None
        if custom_node_type == "category" and custom_family:
            return custom_family, (custom_category or label or None)

    if label == "All" or node_id == "All":
        return None, None

    if node_id.startswith("Family_"):
        return node_id.removeprefix("Family_"), None

    if node_id.startswith("Cat_"):
        payload = node_id.removeprefix("Cat_")
        if "_" in payload:
            family, category = payload.split("_", 1)
            return family, category
        guessed_family = _get_family(label) if label else None
        return guessed_family, label or None

    if label in FAMILIES or label == "Other":
        return label, None

    if parent.startswith("Family_"):
        family = parent.removeprefix("Family_")
        return family, label or None

    if parent in FAMILIES or parent == "Other":
        return parent, label or None

    if label:
        family = _get_family(label)
        return family, label

    return None, None


def _apply_sunburst_selection(event_state: Any, point_lookup: dict[int, dict[str, str]]) -> None:
    points = _extract_selection_points(event_state)
    if not points:
        return

    point = points[-1]
    signature = json.dumps(point, sort_keys=True, default=str)
    if signature == st.session_state.get("fw_last_sunburst_signature"):
        return
    st.session_state.fw_last_sunburst_signature = signature

    selected_family, selected_category = _parse_sunburst_point(point, point_lookup)
    if not selected_family:
        return

    previous_family = st.session_state.get("fw_selected_family")
    st.session_state.fw_selected_family = selected_family

    if selected_category:
        st.session_state.fw_selected_subcategory = selected_category
    else:
        if previous_family != selected_family:
            st.session_state.fw_selected_subcategory = None


def _build_family_scatter(df_plot: pd.DataFrame, family: str, selected_subcategory: str | None) -> go.Figure:
    if df_plot.empty:
        return px.scatter(title="No data")

    scatter_df = df_plot.copy()
    scatter_df["votes_plot"] = scatter_df["votes"].clip(lower=1)
    scatter_df["sex_display"] = (
        scatter_df["sex"].fillna("").astype(str).str.strip().replace("", "-").str.capitalize()
    )

    title_label = selected_subcategory if selected_subcategory else family
    x_min = float(scatter_df["rating"].min()) if not scatter_df["rating"].isna().all() else 0.0
    x_max = float(scatter_df["rating"].max()) if not scatter_df["rating"].isna().all() else 5.0

    fig = px.scatter(
        scatter_df,
        x="rating",
        y="votes_plot",
        hover_name="name",
        size="votes",
        size_max=48,
        color="rating",
        color_continuous_scale=_family_colorscale(family),
        labels={"rating": "Rating", "votes_plot": "Votes"},
        title=f"{title_label} — Rating vs Votes",
        custom_data=["votes", "fragrance_category", "brand", "sex_display", "url"],
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Brand: %{customdata[2]}<br>"
            "Category: %{customdata[1]}<br>"
            "Audience: %{customdata[3]}<br>"
            "Rating: %{x:.2f}<br>"
            "Votes: %{customdata[0]:,}<extra></extra>"
        ),
        marker=dict(line=dict(width=0.5, color="rgba(0,0,0,0.2)")),
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        title=dict(x=0.5, xanchor="center", font=dict(size=24, family="Arial, sans-serif")),
        height=900,
        margin=dict(l=80, r=80, t=70, b=80),
        hovermode="closest",
        clickmode="event",
        coloraxis_colorbar=dict(title="Rating", ticks="outside"),
        xaxis=dict(
            title="Rating",
            range=[x_min - 0.1, x_max + 0.1],
            zeroline=False,
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)",
            tickformat=".2f",
        ),
        yaxis=dict(
            title="Votes (log scale)",
            type="log",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)",
        ),
        autosize=True,
    )

    try:
        fig.add_vrect(
            x0=4.0,
            x1=x_max + 0.2,
            fillcolor="LightGreen",
            opacity=0.08,
            line_width=0,
            annotation_text="High rating (>=4.0)",
            annotation_position="top left",
        )
    except Exception:
        pass

    return fig


def _build_sunburst(cat_counts: pd.DataFrame) -> tuple[go.Figure, dict[int, dict[str, str]]]:
    total = int(cat_counts["count"].sum())

    family_totals = (
        cat_counts.groupby("family", as_index=False)["count"].sum()
        .sort_values(
            by="family",
            key=lambda s: s.map({name: i for i, name in enumerate(FAMILIES + ["Other"])}).fillna(999),
        )
        .reset_index(drop=True)
    )
    family_total_map = family_totals.set_index("family")["count"].to_dict()

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []
    colors: list[str] = []
    custom_rows: list[list[str]] = []

    ids.append("All")
    labels.append("Fragrance Wheel")
    parents.append("")
    values.append(total)
    colors.append("#ffffff")
    custom_rows.append(["", "", "", "root"])

    for _, row in family_totals.iterrows():
        fam = str(row["family"])
        cnt = int(row["count"])
        pct = (cnt / total * 100) if total else 0.0

        ids.append(f"Family_{fam}")
        labels.append(fam)
        parents.append("All")
        values.append(cnt)
        colors.append(FAMILY_COLORS.get(fam, "#90a4ae"))
        custom_rows.append([f"<b>{fam}</b><br>{cnt:,} perfumes<br>{pct:.1f}% of total", fam, "", "family"])

    for _, row in cat_counts.iterrows():
        cat = str(row["category"])
        cnt = int(row["count"])
        fam = str(row["family"])

        fam_total = int(family_total_map.get(fam, 0))
        pct_total = (cnt / total * 100) if total else 0.0
        pct_family = (cnt / fam_total * 100) if fam_total else 0.0

        light = _lighten_hex_color(FAMILY_COLORS.get(fam, "#90a4ae"))

        ids.append(f"Cat_{fam}_{cat}")
        labels.append(cat)
        parents.append(f"Family_{fam}")
        values.append(cnt)
        colors.append(light)
        custom_rows.append(
            [
                (
                    f"<b>{cat}</b><br>"
                    f"{cnt:,} perfumes<br>"
                    f"{pct_total:.1f}% of all<br>"
                    f"{pct_family:.1f}% of {fam}"
                ),
                fam,
                cat,
                "category",
            ]
        )

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors, line=dict(color="white", width=1.5)),
            hovertemplate="%{customdata[0]}<extra></extra>",
            customdata=custom_rows,
            branchvalues="total",
            maxdepth=3,
            insidetextorientation="radial",
            textfont=dict(size=12),
            sort=False,
        )
    )

    fig.update_layout(
        title=dict(
            text="Fragrance Families and Categories Whell",
            font=dict(size=22),
            x=0.5,
        ),
        margin=dict(t=60, l=0, r=0, b=0),
        height=720,
        clickmode="event+select",
    )
    point_lookup = {
        idx: {"id": ids[idx], "label": labels[idx], "parent": parents[idx]}
        for idx in range(len(ids))
    }
    return fig, point_lookup


def _render_clickable_sunburst(fig: go.Figure) -> Any:
    return render_sunburst_click(
        fig,
        height=760,
        default=None,
        key="fw_sunburst_component",
    )


@st.fragment
def _render_subcategory_section(family_df: pd.DataFrame, selected_family: str) -> None:
    """Fragment: reruns only when subcategory/toggle changes, not on full-page reruns."""
    subcategories = sorted(
        family_df["fragrance_category"].dropna().astype(str).str.strip().unique().tolist()
    )
    if not subcategories:
        st.warning("No subcategories found for the selected family.")
        return

    subcategory_options = _build_subcategory_options(subcategories)

    if st.session_state.fw_selected_subcategory not in subcategory_options:
        st.session_state.fw_selected_subcategory = subcategory_options[0]

    def _on_subcategory_change() -> None:
        new_sub = st.session_state.fw_selected_subcategory
        if st.session_state.get("fc_prev_subcategory") != new_sub:
            st.session_state.fc_show_all = False
            st.session_state.fc_prev_subcategory = new_sub

    # Make selector ~30% shorter than previous width (57.1% -> 40.0%).
    sel_col, _ = st.columns([2, 3])
    with sel_col:
        st.selectbox(
            "Subcategory",
            options=subcategory_options,
            key="fw_selected_subcategory",
            on_change=_on_subcategory_change,
        )

    active_subcategory = st.session_state.fw_selected_subcategory
    df_scope = _filter_by_subcategory_option(family_df, active_subcategory)
    scope_id = f"{_normalise_label(selected_family)}::{_normalise_label(active_subcategory)}"
    sex_counts = _build_sex_counts(df_scope)
    _sync_page3_sex_filter_state(sex_counts, scope_id)

    selected_sexes = _selected_page3_sexes()
    df_family_plot = df_scope[df_scope["sex"].isin(selected_sexes)].copy()

    total_frags = int(len(df_family_plot))
    total_votes = float(df_family_plot["votes"].sum()) if total_frags else 0.0
    consistency_score = 0.0
    weighted_avg_rating_display = "N/A"
    total_frags_pct = 0.5
    consistency_pct = 0.5
    weighted_rating_pct = 0.5

    if total_frags > 0:
        noise_threshold = float(df_family_plot["votes"].quantile(0.27))
        qualified_df = df_family_plot[df_family_plot["votes"] > noise_threshold]
        if len(qualified_df) > 0:
            consistency_score = float((qualified_df["rating"] > 4.0).mean() * 100)

        scope_df = family_df[family_df["sex"].isin(selected_sexes)].copy()
        if not scope_df.empty:
            if _is_family_option(active_subcategory):
                scope_df["_metric_group"] = (
                    scope_df["fragrance_category"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .map(lambda cat: cat.split()[0] if cat else "")
                )
                selected_group = _family_from_option(active_subcategory)
            else:
                scope_df["_metric_group"] = (
                    scope_df["fragrance_category"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )
                selected_group = str(active_subcategory or "").strip()

            scope_df = scope_df[scope_df["_metric_group"].ne("")].copy()
            scope_df["_metric_group_norm"] = scope_df["_metric_group"].map(_normalise_label)
            selected_group_norm = _normalise_label(selected_group)

            if not scope_df.empty and selected_group_norm:
                scope_with_weight = scope_df.assign(
                    rating_x_votes=scope_df["rating"] * scope_df["votes"]
                )
                scope_group_stats = scope_with_weight.groupby(
                    "_metric_group_norm",
                    as_index=False,
                ).agg(
                    total_fragrances=("name", "count"),
                    total_votes=("votes", "sum"),
                    sum_weighted_rating=("rating_x_votes", "sum"),
                )
                scope_group_stats["Weighted_Rating"] = float("nan")

                weighted_base = scope_group_stats[scope_group_stats["total_votes"] > 0].copy()
                if not weighted_base.empty:
                    weighted_base["R"] = (
                        weighted_base["sum_weighted_rating"] / weighted_base["total_votes"]
                    )
                    C = float(
                        weighted_base["sum_weighted_rating"].sum()
                        / weighted_base["total_votes"].sum()
                    )
                    m = float(weighted_base["total_votes"].quantile(0.10))
                    v = weighted_base["total_votes"]
                    R = weighted_base["R"]
                    weighted_base["Weighted_Rating"] = (v / (v + m) * R) + (m / (v + m) * C)
                    scope_group_stats = scope_group_stats.merge(
                        weighted_base[["_metric_group_norm", "Weighted_Rating"]],
                        on="_metric_group_norm",
                        how="left",
                        suffixes=("", "_calc"),
                    )
                    scope_group_stats["Weighted_Rating"] = scope_group_stats["Weighted_Rating_calc"]
                    scope_group_stats = scope_group_stats.drop(columns=["Weighted_Rating_calc"])

                group_noise = (
                    scope_df.groupby("_metric_group_norm")["votes"]
                    .quantile(0.27)
                    .rename("noise_threshold")
                )
                qualified_scope = scope_df.join(group_noise, on="_metric_group_norm")
                qualified_scope = qualified_scope[
                    qualified_scope["votes"] > qualified_scope["noise_threshold"]
                ]
                if not qualified_scope.empty:
                    consistency_by_group = (
                        qualified_scope.groupby("_metric_group_norm")["rating"]
                        .apply(lambda s: (s > 4.0).mean() * 100)
                        .rename("Consistency_Score")
                        .reset_index()
                    )
                    scope_group_stats = scope_group_stats.merge(
                        consistency_by_group,
                        on="_metric_group_norm",
                        how="left",
                    )
                else:
                    scope_group_stats["Consistency_Score"] = float("nan")
                scope_group_stats["Consistency_Score"] = (
                    scope_group_stats["Consistency_Score"].fillna(0.0)
                )

                selected_scope_row = scope_group_stats[
                    scope_group_stats["_metric_group_norm"] == selected_group_norm
                ]
                if not selected_scope_row.empty:
                    selected_row = selected_scope_row.iloc[0]
                    consistency_score = float(selected_row["Consistency_Score"])
                    weighted_rating_value = selected_row["Weighted_Rating"]
                    if pd.notna(weighted_rating_value):
                        weighted_avg_rating_display = f"{float(weighted_rating_value):.2f}"

                    def _pct(value: float, series: pd.Series) -> float:
                        valid = pd.to_numeric(series, errors="coerce").dropna()
                        if valid.empty:
                            return 0.5
                        lo, hi = float(valid.min()), float(valid.max())
                        if hi == lo:
                            return 0.5
                        return max(0.0, min(1.0, (float(value) - lo) / (hi - lo)))

                    total_frags_pct = _pct(float(total_frags), scope_group_stats["total_fragrances"])
                    consistency_pct = _pct(consistency_score, scope_group_stats["Consistency_Score"])
                    if pd.notna(weighted_rating_value):
                        weighted_rating_pct = _pct(
                            float(weighted_rating_value),
                            scope_group_stats["Weighted_Rating"],
                        )

    vote_quantile = 0.50 if total_votes > 150_000 else 0.30
    vote_threshold = float(df_family_plot["votes"].quantile(vote_quantile)) if total_frags > 0 else 0.0
    if not st.session_state.fc_show_all:
        shown = int((df_family_plot["votes"] >= vote_threshold).sum()) if total_frags > 0 else 0
        filter_caption = f"Showing {shown} of {total_frags} fragrances (votes ≥ {vote_threshold:.0f})"
        df_plot = df_family_plot[df_family_plot["votes"] >= vote_threshold].copy()
    else:
        filter_caption = f"Showing all {total_frags} fragrances"
        df_plot = df_family_plot

    sex_button_palette = _build_sex_button_palette(df_plot, selected_family)
    _render_sex_button_palette_css(sex_button_palette)

    mcol1, mcol2, mcol3 = st.columns(3)
    _family_metric_card(
        "Number of fragrances",
        f"{total_frags:,}",
        total_frags_pct,
        selected_family,
        mcol1,
    )
    _family_metric_card(
        "Consistency score",
        f"{consistency_score:.1f}%",
        consistency_pct,
        selected_family,
        mcol2,
    )
    _family_metric_card(
        "Weighted avg rating",
        weighted_avg_rating_display,
        weighted_rating_pct,
        selected_family,
        mcol3,
    )
    st.markdown("<div style='height:0.95rem;'></div>", unsafe_allow_html=True)

    ctrl0, ctrl1, ctrl2, ctrl3 = st.columns([2.2, 1, 1, 1])
    active_segments = (
        int(st.session_state.fc_sex_women)
        + int(st.session_state.fc_sex_unisex)
        + int(st.session_state.fc_sex_men)
    )
    blocked_last_segment_toggle = False

    with ctrl0:
        st.toggle("👁 Show all fragrances", key="fc_show_all")

    with ctrl1:
        women_label = f"Women ({sex_counts['women']})"
        if st.button(
            women_label,
            key="fc_women_filter",
            type="primary" if st.session_state.fc_sex_women else "secondary",
            disabled=sex_counts["women"] == 0,
        ):
            if st.session_state.fc_sex_women and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.fc_sex_women = not st.session_state.fc_sex_women
                st.rerun()

    with ctrl2:
        unisex_label = f"Unisex ({sex_counts['unisex']})"
        if st.button(
            unisex_label,
            key="fc_unisex_filter",
            type="primary" if st.session_state.fc_sex_unisex else "secondary",
            disabled=sex_counts["unisex"] == 0,
        ):
            if st.session_state.fc_sex_unisex and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.fc_sex_unisex = not st.session_state.fc_sex_unisex
                st.rerun()

    with ctrl3:
        men_label = f"Men ({sex_counts['men']})"
        if st.button(
            men_label,
            key="fc_men_filter",
            type="primary" if st.session_state.fc_sex_men else "secondary",
            disabled=sex_counts["men"] == 0,
        ):
            if st.session_state.fc_sex_men and active_segments == 1:
                blocked_last_segment_toggle = True
            else:
                st.session_state.fc_sex_men = not st.session_state.fc_sex_men
                st.rerun()

    status_col, warn_col = st.columns([2.2, 3])
    with status_col:
        st.caption(filter_caption)
    with warn_col:
        if blocked_last_segment_toggle:
            st.caption("At least one segment must stay active.")

    if df_plot.empty:
        st.info("No fragrances match the current subcategory/sex filters.")
    else:
        family_fig = _build_family_scatter(df_plot, selected_family, active_subcategory)
        fig_html = family_fig.to_html(
            include_plotlyjs="cdn",
            full_html=False,
            div_id="family-fragrance-plot",
            config={
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"],
            },
        )
        click_js = """
<script>
(function attachClick(){
  var gd = document.getElementById('family-fragrance-plot');
  if (!gd || typeof gd.on !== 'function') { requestAnimationFrame(attachClick); return; }
  gd.on('plotly_click', function(data){
    try {
      var pt = data && data.points && data.points[0];
      if (!pt) return;
      var cd = pt.customdata;
      var url = Array.isArray(cd) ? cd[4] : undefined;
      if (url && typeof url === 'string' && /^https?:\\/\\//.test(url)) {
        window.open(url, '_blank', 'noopener');
      }
    } catch (e) {}
  });
})();
</script>
"""
        components.html(fig_html + click_js, height=950, scrolling=False)

    # --- Top 10 fragrances section ---
    if _is_family_option(active_subcategory):
        top10_heading = f"Top 10 of all {_family_from_option(active_subcategory).lower()} fragrances"
    else:
        top10_heading = f"Top 10 {active_subcategory.lower()} fragrances"
    st.markdown(f"### {top10_heading}")
    rank_mode = st.radio(
        "Ranking mode",
        options=["Reliable top-rated", "Raw rating"],
        index=0,
        horizontal=True,
        key="fc_top10_mode",
        help="Reliable mode ranks with a confidence-aware score. Raw mode ranks by rating only.",
    )

    min_votes_threshold = int(math.ceil(vote_threshold)) if total_frags > 0 else 0
    percentile_label = int(vote_quantile * 100)
    st.caption(
        f"Top-rated (min {min_votes_threshold:,} votes; {percentile_label}th percentile threshold for current category filters)"
    )

    table_pool = df_family_plot[df_family_plot["votes"] >= min_votes_threshold].copy()
    if table_pool.empty:
        st.info("No fragrances meet the current minimum-votes threshold.")
    else:
        prior_rating = float(df_family_plot["rating"].mean()) if not df_family_plot.empty else 0.0
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
        top10_df["Brand"] = top10_df["brand"].fillna("-").astype(str)

        display_top10 = top10_df[
            ["Rank", "name", "rating", "votes", "Sex", "Brand", "url"]
        ].rename(
            columns={
                "name": "Fragrance",
                "rating": "Rating",
                "votes": "Votes",
                "url": "Link",
            }
        )
        render_top_fragrances_table(display_top10)


FAMILY_OPTION_SUFFIX = " Family (All)"


def _normalise_label(value: Any) -> str:
    """Normalize labels for robust case/spacing-insensitive comparisons."""
    return " ".join(str(value or "").strip().lower().split())


def _is_family_option(option: str) -> bool:
    """Return True if *option* is a family-level select-all entry."""
    return isinstance(option, str) and option.strip().endswith(FAMILY_OPTION_SUFFIX)


def _family_from_option(option: str) -> str:
    """'Woody Family (All)' -> 'Woody'."""
    trimmed = str(option or "").strip()
    if trimmed.endswith(FAMILY_OPTION_SUFFIX):
        return trimmed[: -len(FAMILY_OPTION_SUFFIX)].strip()
    return trimmed


def _build_subcategory_options(categories: list[str]) -> list[str]:
    """Prepend dynamically-derived family options to the individual category list.

    Family names are inferred from the first token of each category value, so
    nothing is hard-coded.  Example:
        ["Woody", "Woody Aquatic", "Woody Aromatic"]
        -> ["Woody Family (All)", "Woody", "Woody Aquatic", "Woody Aromatic"]
    """
    families_seen: dict[str, str] = {}
    cleaned_categories: list[str] = []
    seen_categories: set[str] = set()

    for raw_cat in categories:
        cat = " ".join(str(raw_cat or "").strip().split())
        if not cat:
            continue

        cat_norm = _normalise_label(cat)
        if cat_norm in seen_categories:
            continue
        seen_categories.add(cat_norm)
        cleaned_categories.append(cat)

        first_token = cat.split()[0]
        token_norm = _normalise_label(first_token)
        if token_norm and token_norm not in families_seen:
            families_seen[token_norm] = first_token

    family_opts = sorted(
        f"{family_name}{FAMILY_OPTION_SUFFIX}" for family_name in families_seen.values()
    )
    return family_opts + cleaned_categories


def _filter_by_subcategory_option(df: pd.DataFrame, option: str) -> pd.DataFrame:
    """Filter *df* by subcategory dropdown option.

    * Family option (e.g. 'Woody Family (All)'): keeps rows where fragrance_category
      equals the family name *or* starts with it followed by a space.
    * Normal option: exact match on fragrance_category.
    Both comparisons are case-insensitive and whitespace-trimmed.
    """
    if df.empty:
        return df.copy()

    option_norm = _normalise_label(option)
    if not option_norm:
        return df.copy()

    normalised = (
        df["fragrance_category"]
        .fillna("")
        .astype(str)
        .map(_normalise_label)
    )

    if _is_family_option(option):
        family_norm = _normalise_label(_family_from_option(option))
        mask = normalised.eq(family_norm) | normalised.str.startswith(f"{family_norm} ")
        return df[mask].copy()

    return df[normalised.eq(option_norm)].copy()


def _init_state() -> None:
    defaults = {
        "fw_selected_family": None,
        "fw_selected_subcategory": None,
        "fw_last_sunburst_signature": None,
        "fc_show_all": False,
        "fc_prev_scope": None,
        "fc_sex_women": True,
        "fc_sex_unisex": True,
        "fc_sex_men": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    st.set_page_config(
        page_title="Fragrance Categories",
        page_icon="🏷️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --border-subtle: #e5e7eb;
            --text-strong: #111827;
            --text-muted: #64748b;
            --accent: #0f766e;
            --accent-hover: #115e59;
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

        /* Constrain dropdown height to prevent browser scroll-to-fit jumps */
        div[data-baseweb="popover"] ul,
        ul[data-baseweb="menu"],
        div[role="listbox"] ul {
            max-height: 400px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Fragrance Categories Explorer")

    if not MASTER_CSV.exists():
        st.error(f"Data file not found: `{MASTER_CSV}`")
        st.stop()

    _init_state()

    raw_df = _load_raw_data(MASTER_CSV)
    if "fragrance_category" not in raw_df.columns:
        st.error("Column `fragrance_category` is missing in the source data.")
        st.stop()

    cat_counts = _build_category_counts(raw_df)
    if cat_counts.empty:
        st.warning("No fragrance categories available to plot.")
        st.stop()

    st.caption("Click a scent family to explore its fragrances and subcategories.")

    fig, point_lookup = _build_sunburst(cat_counts)
    sunburst_event = _render_clickable_sunburst(fig)
    _apply_sunburst_selection(sunburst_event, point_lookup)

    plot_df = _prepare_family_plot_df(raw_df)
    selected_family = st.session_state.get("fw_selected_family")

    if selected_family:
        st.markdown("---")
        st.subheader(f"{selected_family} Family Explorer")

        family_df = plot_df[plot_df["family"] == selected_family].copy()
        if family_df.empty:
            st.warning("No fragrance records with valid rating/votes found for this family.")
        else:
            _render_subcategory_section(family_df, selected_family)

if __name__ == "__main__":
    main()

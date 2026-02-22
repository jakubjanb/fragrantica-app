"""
Subpage: Fragrance Categories

Visualize fragrance families and categories using a two-level sunburst chart.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.sunburst_component import render_sunburst_click

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
        df["sex"] = df["sex"].fillna("").astype(str).str.strip().str.capitalize()

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
        st.session_state.fw_show_all_subcategories = False
        st.session_state.fw_selected_subcategory = selected_category
    else:
        st.session_state.fw_show_all_subcategories = True
        if previous_family != selected_family:
            st.session_state.fw_selected_subcategory = None


def _build_family_scatter(df_plot: pd.DataFrame, family: str, selected_subcategory: str | None) -> go.Figure:
    if df_plot.empty:
        return px.scatter(title="No data")

    scatter_df = df_plot.copy()
    scatter_df["votes_plot"] = scatter_df["votes"].clip(lower=1)

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
        custom_data=["votes", "fragrance_category", "brand", "sex"],
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
    labels.append("All")
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
            text="Fragrance Families and Categories - Sunburst",
            font=dict(size=18),
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


def _init_state() -> None:
    defaults = {
        "fw_selected_family": None,
        "fw_selected_subcategory": None,
        "fw_show_all_subcategories": True,
        "fw_last_sunburst_signature": None,
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

    st.title("Fragrance Categories Explorer")
    st.markdown("Family-level and category-level composition based on `fragrance_category`.")

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

    total = int(cat_counts["count"].sum())
    unique_categories = int(cat_counts["category"].nunique())
    unique_families = int(cat_counts["family"].nunique())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Perfumes with category", f"{total:,}")
    mc2.metric("Distinct categories", f"{unique_categories:,}")
    mc3.metric("Families represented", f"{unique_families:,}")

    st.caption("Click any family or category segment to explore all fragrances in that family below.")

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
            subcategories = sorted(family_df["fragrance_category"].dropna().astype(str).str.strip().unique().tolist())
            if not subcategories:
                st.warning("No subcategories found for the selected family.")
            else:
                if st.session_state.fw_selected_subcategory not in subcategories:
                    st.session_state.fw_selected_subcategory = subcategories[0]

                ctrl1, ctrl2 = st.columns([2.2, 3.8])
                with ctrl1:
                    st.toggle("👁 All subcategories", key="fw_show_all_subcategories")
                with ctrl2:
                    st.selectbox(
                        "Subcategory",
                        options=subcategories,
                        key="fw_selected_subcategory",
                        disabled=st.session_state.fw_show_all_subcategories,
                    )

                if st.session_state.fw_show_all_subcategories:
                    df_family_plot = family_df
                    filter_caption = (
                        f"Showing all {len(df_family_plot)} fragrances across {len(subcategories)} subcategories"
                    )
                    active_subcategory = None
                else:
                    active_subcategory = st.session_state.fw_selected_subcategory
                    df_family_plot = family_df[family_df["fragrance_category"] == active_subcategory].copy()
                    filter_caption = f"Showing {len(df_family_plot)} fragrances in {active_subcategory}"

                total_frags = int(len(df_family_plot))
                high_rating_count = int((df_family_plot["rating"] >= 4.0).sum()) if total_frags else 0
                pct_high = (high_rating_count / total_frags) if total_frags else 0.0
                total_votes = float(df_family_plot["votes"].sum()) if total_frags else 0.0
                weighted_avg = (
                    float((df_family_plot["rating"] * df_family_plot["votes"]).sum() / total_votes)
                    if total_votes > 0
                    else None
                )
                weighted_avg_display = f"{weighted_avg:.2f}" if weighted_avg is not None else "N/A"

                mcol1, mcol2, mcol3 = st.columns(3)
                with mcol1:
                    st.metric(label="Number of fragrances", value=f"{total_frags}")
                with mcol2:
                    st.metric(label="Rating ≥ 4.0", value=f"{pct_high:.1%}")
                with mcol3:
                    st.metric(label="Weighted avg rating", value=weighted_avg_display)

                st.caption("Metrics are calculated within current filters.")
                st.caption(filter_caption)

                if df_family_plot.empty:
                    st.info("No fragrances match the current subcategory filter.")
                else:
                    family_fig = _build_family_scatter(df_family_plot, selected_family, active_subcategory)
                    st.plotly_chart(
                        family_fig,
                        use_container_width=True,
                        config={
                            "displaylogo": False,
                            "modeBarButtonsToRemove": ["pan2d", "lasso2d", "select2d"],
                        },
                    )

    with st.expander("Category counts table"):
        table_df = cat_counts.sort_values("count", ascending=False).reset_index(drop=True)
        st.dataframe(table_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

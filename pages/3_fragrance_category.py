"""
Subpage: Fragrance Categories

Visualize fragrance families and categories using a two-level sunburst chart.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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


def _build_sunburst(cat_counts: pd.DataFrame) -> go.Figure:
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
    hovers: list[str] = []

    ids.append("All")
    labels.append("All")
    parents.append("")
    values.append(total)
    colors.append("#ffffff")
    hovers.append("")

    for _, row in family_totals.iterrows():
        fam = str(row["family"])
        cnt = int(row["count"])
        pct = (cnt / total * 100) if total else 0.0

        ids.append(f"Family_{fam}")
        labels.append(fam)
        parents.append("All")
        values.append(cnt)
        colors.append(FAMILY_COLORS.get(fam, "#90a4ae"))
        hovers.append(f"<b>{fam}</b><br>{cnt:,} perfumes<br>{pct:.1f}% of total")

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
        hovers.append(
            f"<b>{cat}</b><br>"
            f"{cnt:,} perfumes<br>"
            f"{pct_total:.1f}% of all<br>"
            f"{pct_family:.1f}% of {fam}"
        )

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            marker=dict(colors=colors, line=dict(color="white", width=1.5)),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hovers,
            branchvalues="total",
            maxdepth=3,
            insidetextorientation="radial",
            textfont=dict(size=12),
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
    )
    return fig


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

    fig = _build_sunburst(cat_counts)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Category counts table"):
        table_df = cat_counts.sort_values("count", ascending=False).reset_index(drop=True)
        st.dataframe(table_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

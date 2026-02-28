"""UI-free domain logic for shelf analytics and recommendations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.shelf.constants import FAMILY_COLORS, FAMILY_KEYWORDS, FAMILY_ORDER, TOTAL_WHEEL_CATEGORIES
from src.shelf.utils import _item_key, _lower_or_empty, _normalize_sex


def compute_family(category: Any) -> str:
    text = _lower_or_empty(category)
    if not text:
        return "Other"

    for family in FAMILY_ORDER:
        if family.lower() != "other" and text.startswith(family.lower()):
            return family

    for family, keywords in FAMILY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return family

    return "Other"


def _enrich_shelf_with_catalog(df_shelf: pd.DataFrame, df_catalog: pd.DataFrame) -> pd.DataFrame:
    if df_shelf.empty:
        return df_shelf.copy()

    shelf = df_shelf.copy()
    catalog = df_catalog.copy()

    shelf["brand_norm"] = shelf["brand"].apply(_lower_or_empty)
    shelf["name_norm"] = shelf["name"].apply(_lower_or_empty)
    catalog["brand_norm"] = catalog["brand"].apply(_lower_or_empty)
    catalog["name_norm"] = catalog["name"].apply(_lower_or_empty)

    lookup_cols = ["brand_norm", "name_norm", "fragrance_category", "sex", "rating", "votes", "fragrance_id"]
    lookup = (
        catalog[lookup_cols]
        .drop_duplicates(subset=["brand_norm", "name_norm"])
        .rename(columns={"fragrance_id": "fragrance_id_catalog"})
    )

    merged = shelf.merge(lookup, on=["brand_norm", "name_norm"], how="left")

    if "fragrance_id_catalog" in merged.columns:
        merged["fragrance_id"] = merged["fragrance_id"].combine_first(merged["fragrance_id_catalog"])
    merged["sex"] = merged["sex"].fillna("").apply(_normalize_sex)
    merged["fragrance_category"] = merged["fragrance_category"].fillna("")
    return merged.drop(columns=[c for c in ("brand_norm", "name_norm", "fragrance_id_catalog") if c in merged.columns])


def recommend(
    df_catalog: pd.DataFrame,
    df_shelf: pd.DataFrame,
    user_pref_sex: str,
    top_n: int = 10,
) -> pd.DataFrame:
    if df_catalog.empty:
        return pd.DataFrame()

    catalog = df_catalog.copy()
    shelf = df_shelf.copy() if df_shelf is not None else pd.DataFrame()

    if "catalog_key" not in catalog.columns:
        catalog["catalog_key"] = catalog.apply(
            lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
            axis=1,
        )

    shelf_keys: set[str] = set()
    if not shelf.empty:
        shelf_keys = set(
            shelf.apply(
                lambda row: _item_key(row.get("brand"), row.get("name"), row.get("fragrance_id")),
                axis=1,
            ).tolist()
        )

    candidates = catalog.loc[~catalog["catalog_key"].isin(shelf_keys)].copy()
    if candidates.empty:
        return pd.DataFrame()

    candidates["family"] = candidates["fragrance_category"].apply(compute_family)
    candidates["sex"] = candidates["sex"].apply(_normalize_sex)

    family_pref: dict[str, float] = {}
    if not shelf.empty:
        if "fragrance_category" not in shelf.columns:
            shelf["fragrance_category"] = ""
        shelf["family"] = shelf["fragrance_category"].apply(compute_family)

        ratings = pd.to_numeric(shelf.get("user_rating"), errors="coerce")
        if ratings.notna().any():
            shelf["pref_weight"] = ratings.fillna(ratings.median()).clip(1, 10)
        else:
            shelf["pref_weight"] = 1.0

        weight_by_family = shelf.groupby("family", dropna=False)["pref_weight"].sum()
        if not weight_by_family.empty:
            max_weight = float(weight_by_family.max())
            if max_weight > 0:
                family_pref = {fam: float(w) / max_weight for fam, w in weight_by_family.to_dict().items()}

    if family_pref:
        candidates["category_score"] = candidates["family"].map(family_pref).fillna(0.0)
    else:
        candidates["category_score"] = 0.5

    pref_sex = _normalize_sex(user_pref_sex)
    if pref_sex in {"", "auto"}:
        pref_sex = ""
        if not shelf.empty and "sex" in shelf.columns:
            shelf_sex = shelf["sex"].fillna("").apply(_normalize_sex)
            sex_counts = shelf_sex[shelf_sex != ""].value_counts()
            if not sex_counts.empty:
                pref_sex = str(sex_counts.index[0])

    def score_sex(candidate_sex: str, preference: str) -> float:
        if not preference or preference == "any":
            return 0.5
        if not candidate_sex:
            return 0.4
        if candidate_sex == preference:
            return 1.0
        if candidate_sex == "unisex" and preference in {"woman", "men"}:
            return 0.85
        if preference == "unisex" and candidate_sex in {"woman", "men"}:
            return 0.75
        return 0.0

    candidates["sex_score"] = candidates["sex"].apply(lambda s: score_sex(s, pref_sex))

    has_quality = (
        "rating" in candidates.columns
        and "votes" in candidates.columns
        and candidates["rating"].notna().any()
    )
    if has_quality:
        max_rating = float(candidates["rating"].dropna().max()) if candidates["rating"].notna().any() else 5.0
        rating_div = 10.0 if max_rating > 5.5 else 5.0
        rating_norm = (pd.to_numeric(candidates["rating"], errors="coerce") / rating_div).clip(0, 1).fillna(0.0)
        votes = pd.to_numeric(candidates["votes"], errors="coerce").clip(lower=0).fillna(0.0)
        votes_norm = np.log1p(votes)
        max_votes_norm = float(votes_norm.max()) if len(votes_norm) else 0.0
        if max_votes_norm > 0:
            votes_norm = votes_norm / max_votes_norm
        quality = rating_norm * (0.7 + 0.3 * votes_norm)
        candidates["quality_score"] = quality.fillna(0.0)
    else:
        candidates["quality_score"] = 0.0

    w_cat, w_sex, w_quality = 0.5, 0.3, 0.2
    if not has_quality:
        denom = w_cat + w_sex
        w_cat = w_cat / denom
        w_sex = w_sex / denom
        w_quality = 0.0

    candidates["score"] = (
        w_cat * candidates["category_score"]
        + w_sex * candidates["sex_score"]
        + w_quality * candidates["quality_score"]
    )
    candidates = candidates.sort_values("score", ascending=False).reset_index(drop=True)

    selected_rows: list[dict[str, Any]] = []
    per_family_count: dict[str, int] = {}
    for _, row in candidates.iterrows():
        family = str(row.get("family", "Other"))
        if per_family_count.get(family, 0) >= 3:
            continue
        selected_rows.append(row.to_dict())
        per_family_count[family] = per_family_count.get(family, 0) + 1
        if len(selected_rows) >= top_n:
            break

    if not selected_rows:
        return pd.DataFrame()

    out = pd.DataFrame(selected_rows)
    preferred_cols = ["brand", "name", "sex", "fragrance_category", "rating", "votes", "family", "score", "fragrance_id"]
    existing_cols = [c for c in preferred_cols if c in out.columns]
    return out[existing_cols].copy()


def coverage_stats(df_shelf_with_catalog: pd.DataFrame) -> dict[str, Any]:
    total_categories = TOTAL_WHEEL_CATEGORIES

    if df_shelf_with_catalog.empty:
        empty_counts = pd.DataFrame({"family": FAMILY_ORDER, "count": [0] * len(FAMILY_ORDER)})
        return {
            "coverage_pct": 0.0,
            "covered_families": 0,
            "total_families": len(FAMILY_ORDER),
            "category_coverage_pct": 0.0,
            "covered_categories": 0,
            "total_categories": total_categories,
            "family_counts": empty_counts,
        }

    categories = df_shelf_with_catalog.get("fragrance_category", pd.Series([], dtype=str)).fillna("")
    normalized_categories = categories.apply(_normalize_category_label)
    families = normalized_categories.apply(compute_family)
    family_counts = families.value_counts().to_dict()

    covered_categories = int(normalized_categories[normalized_categories != ""].nunique())
    covered_categories_capped = min(covered_categories, total_categories)
    category_coverage_pct = 100.0 * covered_categories_capped / total_categories if total_categories else 0.0

    counts_df = pd.DataFrame(
        {
            "family": FAMILY_ORDER,
            "count": [int(family_counts.get(f, 0)) for f in FAMILY_ORDER],
        }
    )

    covered = int((counts_df["count"] > 0).sum())
    total = len(FAMILY_ORDER)
    coverage_pct = 100.0 * covered / total if total else 0.0

    return {
        "coverage_pct": coverage_pct,
        "covered_families": covered,
        "total_families": total,
        "category_coverage_pct": category_coverage_pct,
        "covered_categories": covered_categories_capped,
        "total_categories": total_categories,
        "family_counts": counts_df,
    }


def _lighten_hex(hex_color: str, factor: float = 0.45) -> str:
    """Blend a hex color toward white by the given factor (0 = no change, 1 = white)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _normalize_category_label(value: Any) -> str:
    """Normalize category label by trimming and collapsing repeated whitespace."""
    text = str(value).strip()
    if not text:
        return ""
    return " ".join(text.split())


def _build_sunburst_data(df_shelf_enriched: pd.DataFrame) -> dict[str, Any]:
    """
    Build the ids/labels/parents/values/colors/customdata arrays for a
    two-ring Plotly Sunburst chart.

    Inner ring  - one segment per family in FAMILY_ORDER.
    Outer ring  - category breakdown; empty families get a phantom grey
                  child so their inner-ring sector stays visible.
    """
    _EMPTY_COLOR = "#e8ecef"
    _EMPTY_CHILD_COLOR = "#f1f4f6"

    # Accumulate category counts per family.
    family_to_subcats: dict[str, dict[str, int]] = {f: {} for f in FAMILY_ORDER}

    if not df_shelf_enriched.empty and "fragrance_category" in df_shelf_enriched.columns:
        for cat_raw in df_shelf_enriched["fragrance_category"].fillna(""):
            cat = _normalize_category_label(cat_raw)
            family = compute_family(cat)
            subcat_found = cat if cat else "Uncategorized"

            subcat_dict = family_to_subcats[family]
            subcat_dict[subcat_found] = subcat_dict.get(subcat_found, 0) + 1

    total_items: int = sum(sum(sc.values()) for sc in family_to_subcats.values())

    # Phantom value for zero-count families so inner slices remain visible.
    phantom = max(0.3, total_items / len(FAMILY_ORDER) * 0.12) if total_items > 0 else 1.0

    # Build Plotly arrays.
    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[float] = []
    colors: list[str] = []
    customdata: list[dict[str, Any]] = []

    for family in FAMILY_ORDER:
        subcat_counts = family_to_subcats[family]
        family_count = sum(subcat_counts.values())
        fam_color = FAMILY_COLORS.get(family, "#94a3b8")
        fam_id = f"fam::{family}"

        if family_count == 0:
            ids.append(fam_id)
            labels.append(family)
            parents.append("")
            values.append(phantom)
            colors.append(_EMPTY_COLOR)
            customdata.append({"family": family, "count": 0, "total": total_items, "is_empty": True})

            ids.append(f"{fam_id}::__empty__")
            labels.append("No fragrances")
            parents.append(fam_id)
            values.append(phantom)
            colors.append(_EMPTY_CHILD_COLOR)
            customdata.append({"family": family, "count": 0, "total": total_items, "is_empty": True})
        else:
            ids.append(fam_id)
            labels.append(family)
            parents.append("")
            values.append(float(family_count))
            colors.append(fam_color)
            customdata.append({"family": family, "count": family_count, "total": total_items, "is_empty": False})

            subcat_color = _lighten_hex(fam_color, 0.42)
            for subcat_name, subcat_count in sorted(
                subcat_counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            ):
                ids.append(f"{fam_id}::{subcat_name}")
                labels.append(subcat_name)
                parents.append(fam_id)
                values.append(float(subcat_count))
                colors.append(subcat_color)
                customdata.append(
                    {
                        "family": family,
                        "subcat": subcat_name,
                        "count": subcat_count,
                        "total": total_items,
                        "is_empty": False,
                    }
                )

    return {
        "ids": ids,
        "labels": labels,
        "parents": parents,
        "values": values,
        "colors": colors,
        "customdata": customdata,
        "total_items": total_items,
    }


def _coerce_user_rating(value: Any) -> tuple[int | None, str | None]:
    if value is None or pd.isna(value):
        return None, None

    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return None, None
        raw = text
    else:
        raw = value

    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return None, "Rating must be an integer between 1 and 10."

    if not np.isfinite(parsed):
        return None, "Rating must be an integer between 1 and 10."

    rounded = round(parsed)
    if abs(parsed - rounded) > 1e-9:
        return None, "Rating must be an integer between 1 and 10."

    rating = int(rounded)
    if rating < 1 or rating > 10:
        return None, "Rating must be an integer between 1 and 10."
    return rating, None


def _sort_shelf_default(df_view: pd.DataFrame) -> pd.DataFrame:
    """Default shelf ordering: Your rating desc, then Brand/Fragrance asc."""
    if df_view.empty:
        return df_view
    return df_view.sort_values(
        by=["Your rating", "Brand", "Fragrance"],
        ascending=[False, True, True],
        na_position="last",
        kind="mergesort",
    )

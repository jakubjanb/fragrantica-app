"""
Subpage: Fragrance Shelf

MVP features:
- Supabase auth (email/password)
- User shelf CRUD (public.user_shelf)
- Simple content-based recommendations
- Fragrance wheel family coverage
"""

from __future__ import annotations

from html import escape
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import numpy as np
import pandas as pd
import streamlit as st

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - handled in runtime with user-facing error
    Client = Any  # type: ignore[assignment]
    create_client = None  # type: ignore[assignment]


ENABLE_RECOMMENDATION_LOG = False

FAMILY_ORDER = [
    "Floral",
    "Woody",
    "Citrus",
    "Oriental",
    "Aromatic",
    "Chypre",
    "Leather",
    "Fruity",
    "Gourmand",
    "Fresh",
    "Other",
]

FAMILY_KEYWORDS: dict[str, list[str]] = {
    "Floral": ["floral", "flower", "rose", "white floral", "iris", "violet", "jasmine"],
    "Woody": ["woody", "wood", "sandalwood", "cedar", "oud", "vetiver", "patchouli"],
    "Citrus": ["citrus", "bergamot", "lemon", "orange", "grapefruit", "lime", "mandarin"],
    "Oriental": ["oriental", "amber", "spicy", "incense", "resin", "balsamic"],
    "Aromatic": ["aromatic", "herbal", "lavender", "green", "fougere"],
    "Chypre": ["chypre", "oakmoss", "mossy"],
    "Leather": ["leather", "suede", "animalic"],
    "Fruity": ["fruity", "fruit", "apple", "pear", "berry", "peach", "plum"],
    "Gourmand": ["gourmand", "vanilla", "caramel", "chocolate", "sweet", "coffee", "cacao"],
    "Fresh": ["fresh", "aquatic", "marine", "ozonic", "clean", "aldehydic", "soapy"],
}


def _inject_page_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --border-subtle: #e5e7eb;
            --text-strong: #111827;
            --text-muted: #64748b;
            --accent: #0f766e;
            --accent-hover: #115e59;
        }

        .main .block-container {
            max-width: 100%;
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 1.5rem;
            padding-bottom: 1rem;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            margin-bottom: 1.25rem;
            line-height: 1.55;
        }

        .section-note {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: -0.1rem;
            margin-bottom: 0.6rem;
        }

        div[data-baseweb="popover"] ul,
        ul[data-baseweb="menu"],
        div[role="listbox"] ul {
            max-height: 400px !important;
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

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            border-radius: 999px;
            font-weight: 600;
            min-height: 2.75rem;
            border: 1px solid #cbd5e1;
            background: var(--surface);
            color: var(--text-strong);
            width: 100%;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            border-color: #94a3b8;
            background: var(--surface-soft);
            color: var(--text-strong);
        }

        div[data-testid="stButton"] > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: var(--accent);
            border-color: var(--accent);
            color: #ffffff;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
            color: #ffffff;
        }

        .meta-row {
            margin-top: 0.3rem;
            margin-bottom: 0.6rem;
        }

        .meta-chip {
            display: inline-block;
            margin: 0 0.4rem 0.35rem 0;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--border-subtle);
            background: var(--surface-soft);
            color: #334155;
            font-size: 0.8rem;
            font-weight: 500;
            line-height: 1.2;
        }

        div[data-testid="stToggle"] label p {
            font-weight: 600;
            color: var(--text-strong);
        }

        @media (max-width: 980px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _lower_or_empty(value: Any) -> str:
    return _normalize_text(value).lower()


def _dict_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_sex(value: Any) -> str:
    raw = _lower_or_empty(value)
    if raw in {"women", "woman", "female", "f"}:
        return "woman"
    if raw in {"men", "man", "male", "m"}:
        return "men"
    if raw in {"unisex", "u"}:
        return "unisex"
    return raw


def _format_sex_label(value: Any) -> str:
    normalized = _normalize_sex(value)
    if normalized == "woman":
        return "Women"
    if normalized == "men":
        return "Men"
    if normalized == "unisex":
        return "Unisex"
    return _normalize_text(value)


def _item_key(brand: Any, name: Any, fragrance_id: Any = None) -> str:
    fid = _normalize_text(fragrance_id)
    if fid:
        return f"id::{fid.lower()}"
    return f"name::{_lower_or_empty(brand)}::{_lower_or_empty(name)}"


def _sync_client_auth(client: Client) -> None:
    access_token = st.session_state.get("sb_access_token")
    refresh_token = st.session_state.get("sb_refresh_token")
    if not access_token or not refresh_token:
        return

    try:
        client.auth.set_session(access_token, refresh_token)
    except TypeError:
        try:
            client.auth.set_session({"access_token": access_token, "refresh_token": refresh_token})
        except Exception:
            pass
    except Exception:
        pass

    # Additional header sync for some supabase-py/postgrest versions.
    try:
        client.postgrest.auth(access_token)
    except Exception:
        pass


def _read_secret(name: str) -> str | None:
    env_val = os.getenv(name)
    if env_val:
        return env_val

    try:
        secret_val = st.secrets.get(name)
    except Exception:
        secret_val = None

    if secret_val:
        return str(secret_val)
    return None


def get_supabase_client() -> Client:
    if create_client is None:
        raise RuntimeError(
            "Missing package 'supabase'. Install it with: pip install supabase"
        )

    supabase_url = _read_secret("SUPABASE_URL")
    supabase_anon_key = _read_secret("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_anon_key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_ANON_KEY (env or st.secrets)."
        )

    client: Client = create_client(supabase_url, supabase_anon_key)
    _sync_client_auth(client)
    return client


def _clear_auth_session() -> None:
    for key in ("auth_user_id", "auth_email", "sb_access_token", "sb_refresh_token"):
        st.session_state.pop(key, None)


def _save_auth_session(auth_response: Any) -> str | None:
    session = _dict_get(auth_response, "session")
    user = _dict_get(auth_response, "user")
    if user is None and session is not None:
        user = _dict_get(session, "user")

    user_id = _dict_get(user, "id")
    email = _dict_get(user, "email")
    access_token = _dict_get(session, "access_token")
    refresh_token = _dict_get(session, "refresh_token")

    if user_id and access_token and refresh_token:
        st.session_state["auth_user_id"] = str(user_id)
        st.session_state["auth_email"] = str(email or "")
        st.session_state["sb_access_token"] = str(access_token)
        st.session_state["sb_refresh_token"] = str(refresh_token)
        return str(user_id)
    return None


def auth_block() -> str | None:
    st.subheader("Account")
    st.markdown(
        '<p class="section-note">Sign in to save your shelf, ratings, and personalized recommendations.</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        current_user_id = st.session_state.get("auth_user_id")
        current_email = st.session_state.get("auth_email")

        if current_user_id:
            info_col, action_col = st.columns([4.5, 1.2])
            with info_col:
                label = current_email or str(current_user_id)
                st.success(f"Signed in as: {label}")
            with action_col:
                if st.button("Sign out", use_container_width=True):
                    try:
                        sb = get_supabase_client()
                        try:
                            sb.auth.sign_out()
                        except Exception:
                            pass
                    except Exception:
                        pass
                    _clear_auth_session()
                    st.rerun()
            return str(current_user_id)

        tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

        with tab_login:
            with st.form("shelf_login_form"):
                login_email = st.text_input("Email", placeholder="you@example.com")
                login_password = st.text_input("Password", type="password")
                login_submit = st.form_submit_button("Sign in", use_container_width=True, type="primary")

            if login_submit:
                if not login_email or not login_password:
                    st.warning("Enter both email and password.")
                else:
                    try:
                        sb = get_supabase_client()
                        response = sb.auth.sign_in_with_password(
                            {"email": login_email, "password": login_password}
                        )
                        user_id = _save_auth_session(response)
                        if user_id:
                            st.success("Signed in successfully.")
                            st.rerun()
                        else:
                            st.error("Sign in did not return a valid user session.")
                    except Exception as exc:
                        st.error(f"Could not sign in: {exc}")

        with tab_signup:
            with st.form("shelf_signup_form"):
                signup_email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
                signup_password = st.text_input("Password", type="password", key="signup_password")
                signup_submit = st.form_submit_button("Create account", use_container_width=True, type="primary")

            if signup_submit:
                if not signup_email or not signup_password:
                    st.warning("Enter both email and password.")
                elif len(signup_password) < 6:
                    st.warning("Password must contain at least 6 characters.")
                else:
                    try:
                        sb = get_supabase_client()
                        response = sb.auth.sign_up(
                            {"email": signup_email, "password": signup_password}
                        )
                        user_id = _save_auth_session(response)
                        if user_id:
                            st.success("Account created and signed in.")
                            st.rerun()
                        else:
                            st.success(
                                "Account created. If email confirmation is enabled, "
                                "confirm your address from your inbox."
                            )
                    except Exception as exc:
                        st.error(f"Could not create account: {exc}")

    return None


@st.cache_data(show_spinner=False)
def load_catalog_df() -> pd.DataFrame:
    df: pd.DataFrame | None = None

    # TODO: align with src.data.py if a dedicated catalog loader is introduced.
    try:
        from src.data import load_fragrances  # type: ignore

        df = load_fragrances()
    except Exception:
        pass

    if df is None:
        try:
            from src.data import get_fragrances_df  # type: ignore

            df = get_fragrances_df()
        except Exception:
            pass

    if df is None:
        try:
            from src import data as data_module  # type: ignore

            if hasattr(data_module, "fragrances"):
                maybe_df = getattr(data_module, "fragrances")
                if isinstance(maybe_df, pd.DataFrame):
                    df = maybe_df.copy()
        except Exception:
            pass

    if df is None:
        from src.data import load_data

        dataset_path = os.getenv("DATASET_CSV_PATH", "Data/all_brands_clean.csv")
        csv_path = Path(dataset_path)
        if not csv_path.is_absolute():
            csv_path = (Path(__file__).resolve().parent.parent / csv_path).resolve()
        df = load_data(csv_path)

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "brand",
                "name",
                "fragrance_id",
                "fragrance_category",
                "sex",
                "rating",
                "votes",
                "catalog_key",
                "display_label",
            ]
        )

    df = df.copy()

    alias_map = {
        "fragrance_category": ["category", "fragrance_family", "family"],
        "sex": ["gender", "target"],
        "fragrance_id": ["id", "perfume_id", "fragrantica_id"],
    }
    for target_col, aliases in alias_map.items():
        if target_col not in df.columns:
            for alias in aliases:
                if alias in df.columns:
                    df[target_col] = df[alias]
                    break

    for required in ("brand", "name"):
        if required not in df.columns:
            raise RuntimeError(
                f"Required column '{required}' is missing in the fragrance catalog."
            )

    if "fragrance_category" not in df.columns:
        df["fragrance_category"] = ""
    if "sex" not in df.columns:
        df["sex"] = ""
    if "fragrance_id" not in df.columns:
        df["fragrance_id"] = pd.NA
    if "rating" not in df.columns:
        df["rating"] = np.nan
    if "votes" not in df.columns:
        df["votes"] = np.nan

    df["brand"] = df["brand"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["fragrance_category"] = df["fragrance_category"].fillna("").astype(str).str.strip()
    df["sex"] = df["sex"].fillna("").astype(str).str.strip().str.lower().map(_normalize_sex)
    df["fragrance_id"] = (
        df["fragrance_id"]
        .where(df["fragrance_id"].notna(), None)
        .apply(lambda x: _normalize_text(x) or None)
    )
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce")

    df = df[(df["brand"] != "") & (df["name"] != "")].copy()
    df["catalog_key"] = df.apply(
        lambda row: _item_key(row["brand"], row["name"], row.get("fragrance_id")), axis=1
    )
    df["display_label"] = df["brand"] + " — " + df["name"]
    df = df.drop_duplicates(subset=["catalog_key"]).reset_index(drop=True)
    return df


def fetch_user_shelf(user_id: str) -> pd.DataFrame:
    sb = get_supabase_client()
    response = (
        sb.table("user_shelf")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = response.data or []
    df = pd.DataFrame(rows)

    expected_cols = [
        "id",
        "user_id",
        "fragrance_id",
        "brand",
        "name",
        "user_rating",
        "created_at",
        "updated_at",
    ]
    if df.empty:
        return pd.DataFrame(columns=expected_cols)

    for col in expected_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df["brand"] = df["brand"].fillna("").astype(str).str.strip()
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["fragrance_id"] = df["fragrance_id"].apply(lambda x: _normalize_text(x) or None)
    df["user_rating"] = pd.to_numeric(df["user_rating"], errors="coerce")
    return df[expected_cols].copy()


def add_to_shelf(user_id: str, item: dict[str, Any], rating: int | None) -> tuple[bool, str]:
    sb = get_supabase_client()
    brand = _normalize_text(item.get("brand"))
    name = _normalize_text(item.get("name"))
    fragrance_id = _normalize_text(item.get("fragrance_id")) or None

    if not brand or not name:
        return False, "Selected catalog row does not contain valid brand/name fields."

    payload = {
        "user_id": user_id,
        "brand": brand,
        "name": name,
        "fragrance_id": fragrance_id,
        "user_rating": int(rating) if rating is not None else None,
    }

    try:
        sb.table("user_shelf").insert(payload).execute()
        return True, "Fragrance added to your shelf."
    except Exception as exc:
        err = str(exc).lower()
        if "duplicate" in err or "unique" in err:
            return False, "This fragrance is already on your shelf."
        return False, f"Could not add fragrance: {exc}"


def update_shelf_rating(row_id: str, rating: int | None) -> tuple[bool, str]:
    sb = get_supabase_client()
    payload = {"user_rating": int(rating) if rating is not None else None}
    try:
        sb.table("user_shelf").update(payload).eq("id", row_id).execute()
        return True, "Rating saved."
    except Exception as exc:
        return False, f"Could not update rating: {exc}"


def delete_shelf_item(row_id: str) -> tuple[bool, str]:
    sb = get_supabase_client()
    try:
        sb.table("user_shelf").delete().eq("id", row_id).execute()
        return True, "Fragrance removed from shelf."
    except Exception as exc:
        return False, f"Could not remove fragrance: {exc}"


def compute_family(category: Any) -> str:
    text = _lower_or_empty(category)
    if not text:
        return "Other"

    for family in FAMILY_ORDER:
        if family.lower() != "other" and family.lower() in text:
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
    if df_shelf_with_catalog.empty:
        empty_counts = pd.DataFrame({"family": FAMILY_ORDER, "count": [0] * len(FAMILY_ORDER)})
        return {
            "coverage_pct": 0.0,
            "covered_families": 0,
            "total_families": len(FAMILY_ORDER),
            "family_counts": empty_counts,
        }

    categories = df_shelf_with_catalog.get("fragrance_category", pd.Series([], dtype=str)).fillna("")
    families = categories.apply(compute_family)
    family_counts = families.value_counts().to_dict()

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
        "family_counts": counts_df,
    }


def _render_add_form(user_id: str, df_catalog: pd.DataFrame) -> None:
    st.subheader("Add fragrance")
    st.markdown(
        '<p class="section-note">Search the catalog and save fragrances to your personal shelf.</p>',
        unsafe_allow_html=True,
    )

    if df_catalog.empty:
        st.warning("The fragrance catalog is empty.")
        return

    option_indexes = df_catalog.index.tolist()
    with st.container(border=True):
        with st.form("add_to_shelf_form", clear_on_submit=True):
            selected_idx = st.selectbox(
                "Fragrance",
                options=option_indexes,
                format_func=lambda i: str(df_catalog.at[i, "display_label"]),
            )
            opt_col, rating_col, submit_col = st.columns([2.3, 2.2, 1.5])
            with opt_col:
                include_rating = st.checkbox("Add personal rating", value=False)
            with rating_col:
                rating = st.slider("Rating (1-10)", 1, 10, 7)
            with submit_col:
                st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)
                add_submit = st.form_submit_button("Add to shelf", use_container_width=True, type="primary")

    if add_submit:
        item = df_catalog.loc[int(selected_idx)].to_dict()
        value = int(rating) if include_rating else None
        ok, message = add_to_shelf(user_id, item, value)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.warning(message)


def _render_shelf_summary(df_shelf_enriched: pd.DataFrame) -> None:
    ratings = pd.to_numeric(df_shelf_enriched.get("user_rating"), errors="coerce")
    rated_count = int(ratings.notna().sum())
    avg_rating = f"{ratings.dropna().mean():.2f}" if ratings.notna().any() else "N/A"

    st.subheader("Shelf summary")
    st.markdown(
        '<p class="section-note">Quick overview of your collection and personal ratings.</p>',
        unsafe_allow_html=True,
    )
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric("Fragrances on shelf", f"{len(df_shelf_enriched)}")
    with mcol2:
        st.metric("Rated fragrances", f"{rated_count}")
    with mcol3:
        st.metric("Average personal rating", avg_rating)


def _render_shelf_list(df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Your shelf")
    st.markdown(
        '<p class="section-note">Review saved items, adjust ratings, or remove fragrances.</p>',
        unsafe_allow_html=True,
    )

    if df_shelf_enriched.empty:
        st.info("Your shelf is empty. Add your first fragrance above.")
        return

    for _, row in df_shelf_enriched.iterrows():
        row_id = str(row.get("id", ""))
        brand = _normalize_text(row.get("brand"))
        name = _normalize_text(row.get("name"))
        category = _normalize_text(row.get("fragrance_category"))
        sex = _format_sex_label(row.get("sex"))
        rating_raw = row.get("user_rating")
        default_rating = "No rating" if pd.isna(rating_raw) else str(int(float(rating_raw)))

        with st.container(border=True):
            st.markdown(f"**{brand} — {name}**")

            chips: list[str] = []
            if category:
                chips.append(f"Category: {category}")
                chips.append(f"Family: {compute_family(category)}")
            if sex:
                chips.append(f"Audience: {sex}")
            if chips:
                chips_html = "".join(
                    f'<span class="meta-chip">{escape(text)}</span>' for text in chips
                )
                st.markdown(
                    f'<div class="meta-row">{chips_html}</div>',
                    unsafe_allow_html=True,
                )

            action_col1, action_col2, action_col3 = st.columns([2.6, 1.2, 1.2])
            with action_col1:
                rating_options = ["No rating"] + [str(i) for i in range(1, 11)]
                try:
                    default_idx = rating_options.index(default_rating)
                except ValueError:
                    default_idx = 0
                selected_rating = st.selectbox(
                    "Your rating",
                    options=rating_options,
                    index=default_idx,
                    key=f"rating_select_{row_id}",
                )
            with action_col2:
                if st.button(
                    "Save",
                    key=f"save_rating_{row_id}",
                    use_container_width=True,
                    type="primary",
                ):
                    new_rating = None if selected_rating == "No rating" else int(selected_rating)
                    ok, message = update_shelf_rating(row_id, new_rating)
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            with action_col3:
                if st.button("Remove", key=f"delete_row_{row_id}", use_container_width=True):
                    ok, message = delete_shelf_item(row_id)
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


def _render_coverage(df_shelf_enriched: pd.DataFrame) -> None:
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

    chart_df = stats["family_counts"].set_index("family")
    st.bar_chart(chart_df["count"])


def _log_recommendations(user_id: str, df_recs: pd.DataFrame) -> None:
    if not ENABLE_RECOMMENDATION_LOG or df_recs.empty:
        return
    if "fragrance_id" not in df_recs.columns:
        return

    records = []
    for _, row in df_recs.iterrows():
        fragrance_id = _normalize_text(row.get("fragrance_id"))
        if not fragrance_id:
            continue
        records.append(
            {
                "user_id": user_id,
                "fragrance_id": fragrance_id,
                "score": float(row.get("score", 0.0)),
            }
        )

    if not records:
        return

    sb = get_supabase_client()
    sb.table("recommendation_log").insert(records).execute()


def _render_recommendations(user_id: str, df_catalog: pd.DataFrame, df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Recommendations")
    st.markdown(
        '<p class="section-note">Get suggestions based on your shelf profile and audience preference.</p>',
        unsafe_allow_html=True,
    )

    sex_options = {
        "Auto (from shelf)": "auto",
        "No preference": "any",
        "Women": "woman",
        "Unisex": "unisex",
        "Men": "men",
    }
    ctrl1, ctrl2 = st.columns([3, 2])
    with ctrl1:
        selected_sex_label = st.selectbox("Preferred audience", options=list(sex_options.keys()))
    with ctrl2:
        top_n = st.slider("Number of recommendations", min_value=5, max_value=20, value=10, step=1)

    recs_df = recommend(
        df_catalog=df_catalog,
        df_shelf=df_shelf_enriched,
        user_pref_sex=sex_options[selected_sex_label],
        top_n=top_n,
    )

    if recs_df.empty:
        st.info("No recommendations yet. Add more fragrances to your shelf.")
        return

    view_df = recs_df.copy()
    if "score" in view_df.columns:
        view_df["score"] = pd.to_numeric(view_df["score"], errors="coerce").round(4)
    view_df = view_df.rename(
        columns={
            "brand": "Brand",
            "name": "Fragrance",
            "sex": "Audience",
            "fragrance_category": "Category",
            "rating": "Rating",
            "votes": "Votes",
            "family": "Family",
            "score": "Score",
        }
    )
    if "Audience" in view_df.columns:
        view_df["Audience"] = view_df["Audience"].apply(_format_sex_label)
    st.dataframe(view_df, use_container_width=True, hide_index=True)

    if ENABLE_RECOMMENDATION_LOG:
        if st.button("Save recommendations to log"):
            try:
                _log_recommendations(user_id, recs_df)
                st.success("Recommendations saved to recommendation_log.")
            except Exception as exc:
                st.error(f"Could not save recommendation_log: {exc}")


def main() -> None:
    st.set_page_config(
        page_title="Fragrance Shelf",
        page_icon="🧴",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_page_styles()
    st.title("Your Fragrance Shelf")
    st.markdown(
        '<p class="subtitle">Build your personal shelf, save your ratings, and discover recommendations tailored to your collection.</p>',
        unsafe_allow_html=True,
    )

    try:
        df_catalog = load_catalog_df()
    except Exception as exc:
        st.error(f"Could not load fragrance catalog: {exc}")
        return

    user_id = auth_block()
    st.divider()

    if not user_id:
        st.info("Sign in to save your shelf and get personalized recommendations.")
        return

    try:
        df_shelf = fetch_user_shelf(user_id)
    except Exception as exc:
        st.error(f"Could not fetch your shelf data: {exc}")
        return

    _render_add_form(user_id, df_catalog)
    st.divider()

    try:
        df_shelf_enriched = _enrich_shelf_with_catalog(df_shelf, df_catalog)
    except Exception as exc:
        st.error(f"Could not join shelf data with catalog: {exc}")
        df_shelf_enriched = df_shelf.copy()

    _render_shelf_summary(df_shelf_enriched)
    st.divider()
    _render_shelf_list(df_shelf_enriched)
    st.divider()
    _render_coverage(df_shelf_enriched)
    st.divider()
    _render_recommendations(user_id, df_catalog, df_shelf_enriched)


if __name__ == "__main__":
    main()

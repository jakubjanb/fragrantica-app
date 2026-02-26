"""
Subpage: Fragrance Shelf

MVP features:
- Supabase auth (email/password)
- User shelf CRUD (public.user_shelf)
- Simple content-based recommendations
- Fragrance wheel family coverage
"""

from __future__ import annotations

import html
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

# Subcategory keyword mapping for the sunburst outer ring.
# Order of keys matters: first match wins.
SUBCATEGORY_MAP: dict[str, dict[str, list[str]]] = {
    "Floral": {
        "White Floral": ["white floral", "white flower"],
        "Rose": ["rose"],
        "Fresh Floral": ["fresh floral"],
        "Soft Floral": ["soft floral", "powdery"],
        "Green Floral": ["green floral", "iris", "violet"],
    },
    "Woody": {
        "Woody Aromatic": ["woody aromatic", "aromatic woody"],
        "Woody Oriental": ["woody oriental"],
        "Sandalwood": ["sandalwood"],
        "Cedar/Oud": ["cedar", "oud"],
        "Dry Wood": ["dry wood", "vetiver", "patchouli"],
    },
    "Oriental": {
        "Oriental Floral": ["oriental floral", "floral oriental"],
        "Oriental Woody": ["oriental woody"],
        "Soft Oriental": ["soft oriental"],
        "Spicy Oriental": ["spicy oriental", "spice"],
    },
    "Fresh": {
        "Aquatic/Marine": ["aquatic", "marine", "ozonic", "water"],
        "Aldehydic": ["aldehydic", "soapy"],
        "Citrus Fresh": ["citrus"],
        "Green Fresh": ["green"],
    },
    "Citrus": {
        "Aromatic Citrus": ["aromatic citrus"],
        "Fruity Citrus": ["fruity citrus"],
        "Hesperidic": ["bergamot", "lemon", "orange", "grapefruit", "lime", "mandarin", "hesperidic"],
    },
    "Aromatic": {
        "Aromatic Fougère": ["fougere", "fougère"],
        "Aromatic Herbal": ["herbal", "lavender"],
        "Aromatic Spicy": ["spicy"],
    },
    "Chypre": {
        "Floral Chypre": ["floral chypre"],
        "Fruity Chypre": ["fruity chypre"],
        "Aromatic Chypre": ["aromatic chypre"],
    },
    "Fruity": {
        "Tropical Fruity": ["tropical", "mango", "passion"],
        "Berry Fruity": ["berry", "strawberry", "raspberry", "blackcurrant"],
        "Peach/Apple": ["peach", "apple", "pear", "apricot"],
    },
    "Gourmand": {
        "Sweet/Vanilla": ["vanilla", "sweet"],
        "Chocolate/Coffee": ["chocolate", "coffee", "cacao"],
        "Caramel": ["caramel", "butterscotch"],
    },
    "Leather": {
        "Smoky Leather": ["smoky", "tobacco"],
        "Suede": ["suede"],
        "Animalic": ["animalic", "musk"],
    },
    "Other": {
        "Uncategorized": [],
    },
}

FAMILY_COLORS: dict[str, str] = {
    "Floral":    "#e879a0",
    "Woody":     "#a0714f",
    "Citrus":    "#d4a017",
    "Oriental":  "#9b59b6",
    "Fresh":     "#38bdf8",
    "Aromatic":  "#6b9e5e",
    "Chypre":    "#2d7d4f",
    "Fruity":    "#f4845f",
    "Gourmand":  "#c9882a",
    "Leather":   "#8b6914",
    "Other":     "#94a3b8",
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

        .account-dock {
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            padding: 0.65rem 0.8rem;
            display: inline-block;
            width: fit-content;
        }

        .account-dock-label {
            margin: 0 0 0.25rem;
            color: #64748b;
            font-size: 0.68rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            font-weight: 700;
        }

        .account-dock-email {
            margin: 0;
            color: #0f172a;
            font-size: 0.9rem;
            font-weight: 600;
            line-height: 1.3;
            white-space: nowrap;
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


def _sign_out_user() -> None:
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


def auth_block(compact_logged_in: bool = False) -> str | None:
    current_user_id = st.session_state.get("auth_user_id")
    current_email = st.session_state.get("auth_email")

    if current_user_id and compact_logged_in:
        label = _normalize_text(current_email) or str(current_user_id)
        safe_label = html.escape(label)
        btn_col, dock_col = st.columns([1, 2.5], vertical_alignment="center")
        with btn_col:
            if st.button("Sign out", key="shelf_sign_out_compact"):
                _sign_out_user()
        with dock_col:
            st.markdown(
                f"""
                <div class="account-dock">
                    <p class="account-dock-label">Account</p>
                    <p class="account-dock-email" title="{safe_label}">{safe_label}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return str(current_user_id)

    st.subheader("Account")
    st.markdown(
        '<p class="section-note">Sign in to save your shelf, ratings, and personalized recommendations.</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if current_user_id:
            info_col, action_col = st.columns([4.5, 1.2])
            with info_col:
                label = current_email or str(current_user_id)
                st.success(f"Signed in as: {label}")
            with action_col:
                if st.button("Sign out", use_container_width=True, key="shelf_sign_out_full"):
                    _sign_out_user()
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
        '<p class="section-note">Pick a brand, then select a fragrance to add to your shelf.</p>',
        unsafe_allow_html=True,
    )

    if df_catalog.empty:
        st.warning("The fragrance catalog is empty.")
        return

    catalog_df = df_catalog.copy()
    if "display_label" not in catalog_df.columns:
        catalog_df["display_label"] = (
            catalog_df.get("brand", "").fillna("").astype(str).str.strip()
            + " — "
            + catalog_df.get("name", "").fillna("").astype(str).str.strip()
        )

    for col in ("brand", "name", "fragrance_category", "sex", "rating", "votes"):
        if col not in catalog_df.columns:
            catalog_df[col] = pd.NA

    catalog_df["brand"] = catalog_df["brand"].fillna("").astype(str).str.strip()
    catalog_df["name"] = catalog_df["name"].fillna("").astype(str).str.strip()
    catalog_df["fragrance_category"] = catalog_df["fragrance_category"].fillna("").astype(str).str.strip()
    catalog_df["display_label"] = catalog_df["display_label"].fillna("").astype(str).str.strip()
    catalog_df = catalog_df.sort_values(by=["brand", "name"], ascending=[True, True], kind="mergesort")

    # Build brand options (sorted A-Z, empty first = no selection)
    brands_list = sorted(
        [b for b in catalog_df["brand"].unique().tolist() if b],
        key=lambda v: v.casefold(),
    )

    add_submit = False
    include_rating = False
    rating = 7

    with st.container(border=True):
        # ── Step 1: Brand autocomplete ────────────────────────────────────
        selected_brand = st.selectbox(
            "Brand",
            options=[""] + brands_list,
            index=0,
            key="shelf_add_brand",
            help="Start typing to find a brand.",
            format_func=lambda b: "Select a brand…" if b == "" else b,
        )

        # Clear fragrance selection when brand changes
        prev_brand = st.session_state.get("_shelf_add_prev_brand", "")
        if selected_brand != prev_brand:
            st.session_state["_shelf_add_prev_brand"] = selected_brand
            st.session_state.pop("shelf_add_selected_idx", None)

        if not selected_brand:
            st.caption(f"{len(brands_list):,} brands available — start typing above.")
            return

        # ── Step 2: Fragrance autocomplete (filtered to brand) ────────────
        brand_catalog = catalog_df[catalog_df["brand"] == selected_brand].copy()
        if brand_catalog.empty:
            st.info("No fragrances found for this brand.")
            return

        frag_count = len(brand_catalog)
        st.caption(f"{frag_count:,} fragrance{'s' if frag_count != 1 else ''} by {selected_brand}")

        option_indexes = brand_catalog.index.tolist()
        selected_idx_key = "shelf_add_selected_idx"
        if selected_idx_key in st.session_state and st.session_state[selected_idx_key] not in option_indexes:
            st.session_state.pop(selected_idx_key)

        selected_idx = st.selectbox(
            "Fragrance",
            options=option_indexes,
            key=selected_idx_key,
            format_func=lambda i: str(brand_catalog.at[i, "name"]),
            help="Start typing to find a fragrance.",
        )

        selected_item = brand_catalog.loc[int(selected_idx)]

        # Detail chips
        chips: list[str] = []
        selected_category = _normalize_text(selected_item.get("fragrance_category"))
        if selected_category:
            chips.append(selected_category)
        selected_sex_label = _format_sex_label(selected_item.get("sex"))
        if selected_sex_label:
            chips.append(selected_sex_label)
        fragrantica_rating = pd.to_numeric(pd.Series([selected_item.get("rating")]), errors="coerce").iloc[0]
        votes_value = pd.to_numeric(pd.Series([selected_item.get("votes")]), errors="coerce").iloc[0]
        if pd.notna(fragrantica_rating):
            rating_chip = f"★ {float(fragrantica_rating):.2f}"
            if pd.notna(votes_value):
                rating_chip += f" · {int(float(votes_value)):,} votes"
            chips.append(rating_chip)

        if chips:
            chips_html = "".join(
                f'<span class="meta-chip">{html.escape(c)}</span>' for c in chips
            )
            st.markdown(f'<div class="meta-row">{chips_html}</div>', unsafe_allow_html=True)

        # Rating + submit
        chk_col, slider_col, btn_col = st.columns([1.5, 2.8, 1.2], vertical_alignment="center")
        with chk_col:
            include_rating = st.checkbox("My rating", value=False, key="shelf_add_include_rating")
        with slider_col:
            rating = st.slider(
                "Rating (1–10)", 1, 10, 7,
                key="shelf_add_rating",
                disabled=not include_rating,
            )
        with btn_col:
            add_submit = st.button(
                "Add to shelf",
                use_container_width=True,
                type="primary",
                key="shelf_add_submit",
            )

    if add_submit:
        item = brand_catalog.loc[int(selected_idx)].to_dict()
        value = int(rating) if include_rating else None
        ok, message = add_to_shelf(user_id, item, value)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.warning(message)


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


def _render_shelf_list(df_shelf_enriched: pd.DataFrame) -> None:
    st.subheader("Your shelf")
    st.markdown(
        '<p class="section-note">Review and update your full shelf in one compact list.</p>',
        unsafe_allow_html=True,
    )

    feedback = st.session_state.pop("shelf_save_feedback", None)
    if feedback:
        st.success(feedback)

    feedback_errors = st.session_state.pop("shelf_save_errors", None)
    if feedback_errors:
        details = "\n- ".join(str(msg) for msg in feedback_errors)
        st.error(f"Some changes could not be saved:\n- {details}")

    if df_shelf_enriched.empty:
        st.info("Your shelf is empty. Add your first fragrance above.")
        return

    shelf_df = df_shelf_enriched.copy()
    for col in ("id", "brand", "name", "fragrance_category", "sex", "user_rating", "rating", "votes"):
        if col not in shelf_df.columns:
            shelf_df[col] = pd.NA

    shelf_df["__row_id"] = shelf_df["id"].apply(_normalize_text)
    invalid_ids = int((shelf_df["__row_id"] == "").sum())
    if invalid_ids:
        st.warning(f"{invalid_ids} shelf item(s) are missing IDs and cannot be edited.")
        shelf_df = shelf_df[shelf_df["__row_id"] != ""].copy()
        if shelf_df.empty:
            return

    shelf_df["Brand"] = shelf_df["brand"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Fragrance"] = shelf_df["name"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Category"] = shelf_df["fragrance_category"].fillna("").astype(str).str.strip().replace("", "-")
    shelf_df["Group"] = shelf_df["fragrance_category"].apply(compute_family)

    your_rating = pd.to_numeric(shelf_df["user_rating"], errors="coerce")
    shelf_df["Your rating"] = your_rating.where(your_rating.between(1, 10)).round().astype("Int64")

    search_query = st.text_input(
        "Search",
        key="shelf_table_search",
        placeholder="Brand, fragrance, category, or group",
    ).strip()

    filtered_df = shelf_df.copy()
    if search_query:
        q = search_query.lower()
        search_blob = (
            filtered_df["Brand"].str.lower()
            + " "
            + filtered_df["Fragrance"].str.lower()
            + " "
            + filtered_df["Category"].str.lower()
            + " "
            + filtered_df["Group"].str.lower()
        )
        filtered_df = filtered_df[search_blob.str.contains(q, na=False)].copy()

    filtered_df = _sort_shelf_default(filtered_df)
    st.caption(f"Showing {len(filtered_df)} of {len(shelf_df)} fragrances")

    if filtered_df.empty:
        st.info("No shelf items match your search.")
        return

    original_ratings = {
        str(row_id): (None if pd.isna(val) else int(val))
        for row_id, val in zip(filtered_df["__row_id"], filtered_df["Your rating"])
    }

    editor_df = filtered_df[
        [
            "__row_id",
            "Brand",
            "Fragrance",
            "Group",
            "Category",
            "Your rating",
        ]
    ].copy()
    # Visual bar column mirrors "Your rating" for a progress-bar display.
    editor_df["Rating bar"] = editor_df["Your rating"]
    editor_df["Remove"] = False
    editor_df = editor_df.set_index("__row_id")
    editor_df.index.name = "row_id"
    editor_df["Your rating"] = pd.to_numeric(editor_df["Your rating"], errors="coerce")
    editor_df["Rating bar"] = pd.to_numeric(editor_df["Rating bar"], errors="coerce")

    table_height = min(900, 38 + len(editor_df) * 35 + 2)
    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        height=table_height,
        key="shelf_table_editor",
        column_order=["Brand", "Fragrance", "Group", "Category", "Your rating", "Rating bar", "Remove"],
        disabled=[
            "Brand",
            "Fragrance",
            "Group",
            "Category",
            "Rating bar",
        ],
        column_config={
            "Your rating": st.column_config.NumberColumn(
                "Your rating",
                min_value=1,
                max_value=10,
                step=1,
                format="%d",
                required=False,
                help="Set personal rating from 1 to 10 or leave empty.",
            ),
            "Rating bar": st.column_config.ProgressColumn(
                "Rating bar",
                min_value=0,
                max_value=10,
                format=" ",
                help="Visual indicator for your rating.",
            ),
            "Remove": st.column_config.CheckboxColumn("Remove"),
        },
    )

    if st.button("Save changes", type="primary", key="save_shelf_changes"):
        updated_count = 0
        removed_count = 0
        errors: list[str] = []

        for row_id, row in edited_df.iterrows():
            row_id_s = str(row_id)
            row_label = f"{row.get('Brand', '-')} — {row.get('Fragrance', '-')}"

            if bool(row.get("Remove", False)):
                ok, message = delete_shelf_item(row_id_s)
                if ok:
                    removed_count += 1
                else:
                    errors.append(f"{row_label}: {message}")
                continue

            new_rating, validation_error = _coerce_user_rating(row.get("Your rating"))
            if validation_error:
                errors.append(f"{row_label}: {validation_error}")
                continue

            old_rating = original_ratings.get(row_id_s)
            if new_rating == old_rating:
                continue

            ok, message = update_shelf_rating(row_id_s, new_rating)
            if ok:
                updated_count += 1
            else:
                errors.append(f"{row_label}: {message}")

        if updated_count == 0 and removed_count == 0 and not errors:
            st.info("No changes to save.")
            return

        summary_parts: list[str] = []
        if updated_count:
            summary_parts.append(f"Saved {updated_count} rating{'s' if updated_count != 1 else ''}")
        if removed_count:
            summary_parts.append(f"Removed {removed_count} fragrance{'s' if removed_count != 1 else ''}")

        if summary_parts:
            st.session_state["shelf_save_feedback"] = ", ".join(summary_parts)
        if errors:
            st.session_state["shelf_save_errors"] = errors[:8]
        st.rerun()


def _lighten_hex(hex_color: str, factor: float = 0.45) -> str:
    """Blend a hex color toward white by the given factor (0 = no change, 1 = white)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_sunburst_data(df_shelf_enriched: pd.DataFrame) -> dict[str, Any]:
    """
    Build the ids/labels/parents/values/colors/customdata arrays for a
    two-ring Plotly Sunburst chart.

    Inner ring  — one segment per family in FAMILY_ORDER.
    Outer ring  — subcategory breakdown; empty families get a phantom grey
                  child so their inner-ring sector stays visible.
    """
    _EMPTY_COLOR = "#e8ecef"
    _EMPTY_CHILD_COLOR = "#f1f4f6"

    # ── Accumulate subcategory counts ─────────────────────────────────────────
    family_to_subcats: dict[str, dict[str, int]] = {f: {} for f in FAMILY_ORDER}

    if not df_shelf_enriched.empty and "fragrance_category" in df_shelf_enriched.columns:
        for cat_raw in df_shelf_enriched["fragrance_category"].fillna(""):
            cat = str(cat_raw).strip()
            family = compute_family(cat)
            cat_lower = cat.lower()

            subcat_found: str | None = None
            if family in SUBCATEGORY_MAP:
                for subcat_name, keywords in SUBCATEGORY_MAP[family].items():
                    if keywords and any(kw in cat_lower for kw in keywords):
                        subcat_found = subcat_name
                        break

            if subcat_found is None:
                subcat_found = "Uncategorized" if family == "Other" else f"Other {family}"

            subcat_dict = family_to_subcats[family]
            subcat_dict[subcat_found] = subcat_dict.get(subcat_found, 0) + 1

    total_items: int = sum(sum(sc.values()) for sc in family_to_subcats.values())

    # Phantom value given to zero-count families so their inner-ring slice
    # stays visible (≈ 12% of the average slot size, min 0.3).
    phantom = max(0.3, total_items / len(FAMILY_ORDER) * 0.12) if total_items > 0 else 1.0

    # ── Build Plotly arrays ───────────────────────────────────────────────────
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
            # Inner ring: phantom grey segment
            ids.append(fam_id)
            labels.append(family)
            parents.append("")
            values.append(phantom)
            colors.append(_EMPTY_COLOR)
            customdata.append({"family": family, "count": 0, "total": total_items, "is_empty": True})

            # Outer ring: single placeholder child
            ids.append(f"{fam_id}::__empty__")
            labels.append("No fragrances")
            parents.append(fam_id)
            values.append(phantom)
            colors.append(_EMPTY_CHILD_COLOR)
            customdata.append({"family": family, "count": 0, "total": total_items, "is_empty": True})
        else:
            # Inner ring: real segment sized by count
            ids.append(fam_id)
            labels.append(family)
            parents.append("")
            values.append(float(family_count))
            colors.append(fam_color)
            customdata.append({"family": family, "count": family_count, "total": total_items, "is_empty": False})

            # Outer ring: one segment per subcategory (only non-zero)
            subcat_color = _lighten_hex(fam_color, 0.42)
            for subcat_name, subcat_count in subcat_counts.items():
                ids.append(f"{fam_id}::{subcat_name}")
                labels.append(subcat_name)
                parents.append(fam_id)
                values.append(float(subcat_count))
                colors.append(subcat_color)
                customdata.append({
                    "family": family,
                    "subcat": subcat_name,
                    "count": subcat_count,
                    "total": total_items,
                    "is_empty": False,
                })

    return {
        "ids": ids,
        "labels": labels,
        "parents": parents,
        "values": values,
        "colors": colors,
        "customdata": customdata,
        "total_items": total_items,
    }


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

    # Build per-node hover text
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
        annotations.append(dict(
            text="Add fragrances<br>to see your coverage",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        ))

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

    # Inline legend — only covered families
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
    subtitle_html = (
        '<p class="subtitle">Build your personal shelf, save your ratings, and discover '
        "recommendations tailored to your collection.</p>"
    )

    if st.session_state.get("auth_user_id"):
        intro_col, account_col = st.columns([4.2, 3.0], gap="large")
        with intro_col:
            st.markdown(subtitle_html, unsafe_allow_html=True)
        with account_col:
            user_id = auth_block(compact_logged_in=True)
    else:
        st.markdown(subtitle_html, unsafe_allow_html=True)
        user_id = None

    try:
        df_catalog = load_catalog_df()
    except Exception as exc:
        st.error(f"Could not load fragrance catalog: {exc}")
        return

    if not user_id:
        user_id = auth_block()

    if not user_id:
        st.info("Sign in to save your shelf and get personalized recommendations.")
        return

    st.divider()

    try:
        df_shelf = fetch_user_shelf(user_id)
    except Exception as exc:
        st.error(f"Could not fetch your shelf data: {exc}")
        return

    _render_add_form(user_id, df_catalog)

    try:
        df_shelf_enriched = _enrich_shelf_with_catalog(df_shelf, df_catalog)
    except Exception as exc:
        st.error(f"Could not join shelf data with catalog: {exc}")
        df_shelf_enriched = df_shelf.copy()

    _render_shelf_list(df_shelf_enriched)
    st.divider()
    _render_coverage(df_shelf_enriched)
    st.divider()
    _render_recommendations(user_id, df_catalog, df_shelf_enriched)


if __name__ == "__main__":
    main()

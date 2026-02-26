"""Authentication and Supabase session handling for shelf page."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from src.shelf.utils import _dict_get, _normalize_text

# Keep env loading behavior available regardless of import site.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

try:
    from supabase import Client, create_client
except Exception:  # pragma: no cover - handled in runtime with user-facing error
    Client = Any  # type: ignore[assignment]
    create_client = None  # type: ignore[assignment]


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

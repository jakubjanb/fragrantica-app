"""Streamlit style injection for fragrance shelf page."""

from __future__ import annotations

import streamlit as st


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

        .coverage-metric-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.675rem;
            margin-bottom: 0.6rem;
        }

        .coverage-metric-card {
            flex: 0 1 calc(36% - 0.675rem);
            max-width: calc(36% - 0.675rem);
            min-width: 234px;
            background: var(--metric-bg, #f8fafc);
            border-radius: 10.8px;
            padding: 0.81rem 0.72rem 0.74rem;
            min-height: 121px;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .coverage-metric-card .coverage-metric-value {
            margin: 0;
            color: var(--metric-color, var(--text-strong));
            font-size: 23px !important;
            font-weight: 700;
            line-height: 1.08;
            letter-spacing: -0.02em;
        }

        .coverage-metric-label {
            margin: 0.225rem 0 0;
            color: #6b7280;
            font-size: 0.7rem;
            font-weight: 600;
            line-height: 1.25;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        .coverage-metric-detail {
            margin: 0.495rem 0 0;
            color: #475569;
            font-size: 0.85rem;
            font-weight: 500;
            line-height: 1.3;
            display: inline-flex;
            align-items: baseline;
            justify-content: center;
            gap: 0.315rem;
            flex-wrap: wrap;
        }

        .coverage-metric-detail-value {
            color: #0f172a;
            font-weight: 500;
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

            .coverage-metric-card {
                flex: 1 1 calc(50% - 0.75rem);
                max-width: none;
                min-width: 198px;
            }
        }

        @media (max-width: 640px) {
            .coverage-metric-card {
                flex: 1 1 100%;
                min-width: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

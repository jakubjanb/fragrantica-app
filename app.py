"""
Streamlit app: Fragrance World (Landing Page)

Usage:
    streamlit run app.py

This is the landing page for the Fragrance World app. Use the navigation to open subpages.
"""

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="Fragrance World",
        page_icon="🧴",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Simple landing UI
    st.title("🧴 Fragrance World")
    st.markdown(
        "Discover and explore perfume ratings and popularity across brands.\n\n"
        "Use the navigation in the sidebar or the button below to open the explorer.")

    st.divider()
    st.subheader("Open Explorer")
    # Prominent link/button to the subpage
    st.page_link("pages/fragrance_explorer.py", label="🚀 Go to Fragrance Explorer", icon="🧭")


if __name__ == "__main__":
    main()

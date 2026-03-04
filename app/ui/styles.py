from __future__ import annotations
import streamlit as st


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; }
        .small-muted { color: rgba(250,250,250,0.65); font-size: 0.85rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

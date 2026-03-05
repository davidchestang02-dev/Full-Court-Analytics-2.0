from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
import streamlit as st


def _b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def set_app_background(image_path: Optional[str]):
    """
    If image_path is None, we switch to a clean dark gradient.
    If provided, we set a premium hero background (NO dark grey overlay layer).
    """
    if image_path:
        data = _b64(image_path)
        if not data:
            return
        st.markdown(
            f"""
            <style>
            .stApp {{
              background:
                radial-gradient(1200px 600px at 20% 10%, rgba(0,170,255,0.22), transparent 60%),
                radial-gradient(900px 500px at 85% 30%, rgba(255,170,0,0.14), transparent 55%),
                linear-gradient(180deg, rgba(6,10,18,0.55), rgba(6,10,18,0.70)),
                url("data:image/png;base64,{data}");
              background-size: cover;
              background-position: center 5%;
              background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp {
              background:
                radial-gradient(1200px 650px at 20% 10%, rgba(0,170,255,0.18), transparent 55%),
                radial-gradient(900px 500px at 85% 30%, rgba(255,170,0,0.10), transparent 55%),
                linear-gradient(180deg, #070b12, #0a0f18);
              background-attachment: fixed;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def inject_global_styles():
    # Remove Streamlit chrome, sidebar, padding issues, make cards feel native
    st.markdown(
        """
        <style>
        /* Hide sidebar completely */
        section[data-testid="stSidebar"] { display: none !important; }
        div[data-testid="collapsedControl"] { display: none !important; }

        /* Hide Streamlit header/footer */
        header[data-testid="stHeader"] { display: none; }
        footer { visibility: hidden; }

        /* Global typography */
        html, body, [class*="css"]  {
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
        }

        /* Reduce default top padding */
        .block-container { padding-top: 1.0rem !important; }

        /* Make buttons look premium */
        .stButton>button {
            border-radius: 14px !important;
            border: 1px solid rgba(255,255,255,0.10) !important;
            background: rgba(255,255,255,0.06) !important;
            color: rgba(255,255,255,0.92) !important;
            padding: 0.6rem 0.9rem !important;
            transition: all 120ms ease-in-out;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            border-color: rgba(0,170,255,0.35) !important;
            background: rgba(0,170,255,0.10) !important;
        }

        /* Inputs */
        .stSelectbox, .stDateInput, .stTextInput {
            border-radius: 14px !important;
        }

        /* Card wrapper */
        .fca-card {
            border: 1px solid rgba(255,255,255,0.10);
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
            border-radius: 18px;
            padding: 14px 14px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }

        .fca-glass {
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(10,14,22,0.58);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 18px;
        }

        .fca-muted { color: rgba(255,255,255,0.65); }
        .fca-title { font-size: 1.15rem; font-weight: 700; letter-spacing: 0.2px; }
        .fca-subtitle { font-size: 0.95rem; color: rgba(255,255,255,0.70); }

        /* Clickable card button */
        div[data-testid="stVerticalBlock"] .fca-card-btn button {
            width: 100% !important;
            text-align: left !important;
            background: transparent !important;
            border: 0 !important;
            padding: 0 !important;
        }

        /* Horizontal separator */
        .fca-hr {
            height: 1px;
            background: rgba(255,255,255,0.10);
            margin: 10px 0;
        }

        /* --- METRIC CARD SYSTEM (Top Plays + Game Blocks) ------------------- */
        .metric-card {
            padding: 1rem 1.25rem;
            border-radius: 0.9rem;
            background: rgba(15,20,35,0.90);
            border: 1px solid rgba(80,120,255,0.45);
            box-shadow: 0 0 18px rgba(0,120,255,0.20);
            transition: 0.25s ease;
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0 26px rgba(0,150,255,0.40);
        }
        .metric-label {
            font-size: 0.80rem;
            text-transform: uppercase;
            color: #a5b4fc;
            letter-spacing: 0.14em;
            text-shadow: 0 0 14px rgba(80,120,255,0.55);
            width: 100%;
            text-align: center;
        }
        .metric-value {
            font-size: 1.55rem;
            font-weight: 800;
            color: #7dd3fc;
            text-shadow: 0 0 10px rgba(0,200,255,0.45);
            width: 100%;
            text-align: center;
            line-height: 1.05;
        }
        .metric-sub {
            font-size: 0.85rem;
            font-weight: 700;
            color: rgba(232,236,255,0.78);
            width: 100%;
            text-align: center;
        }

        .section-divider {
            margin-top: 1.6rem;
            margin-bottom: 1.1rem;
            height: 2px;
            background: linear-gradient(
                to right,
                rgba(0,40,120,0),
                rgba(60,110,255,0.8),
                rgba(0,40,120,0)
            );
            border-radius: 4px;
        }

        /* --- CLICKABLE CARD WITHOUT OVERLAP MESS --------------------------- */
        .fca-card-wrap {
            position: relative;
            border-radius: 0.9rem;
        }

        .fca-card-hitbox button {
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            height: 100% !important;
            opacity: 0 !important;
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        .fca-card-hitbox button p { display:none !important; }

        .fca-card-hitbox { margin: 0 !important; padding: 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

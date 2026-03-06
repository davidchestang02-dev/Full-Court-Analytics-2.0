from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
LANDING_BG_IMAGE = "images/fca_background_1.png"


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if p.exists():
        return p
    repo_relative = REPO_ROOT / path
    if repo_relative.exists():
        return repo_relative
    return p


def _b64(path: str) -> str:
    p = _resolve_path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def inject_global_css(bg_url: str, logo_url: str) -> None:
    st.set_page_config(
        page_title="Full Court Analytics",
        page_icon=logo_url,
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        f"""
<style>
/* ---------- GLOBAL / BACKGROUND ---------- */
html, body, [data-testid="stAppViewContainer"] {{
  height: 100%;
}}
.stApp {{
  background-image: url("{bg_url}");
  background-size: cover;
  background-position: center 5%;
  background-repeat: no-repeat;
  background-attachment: fixed;
  color: #e8ecff;
  font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}}

/* IMPORTANT: remove the dark overlay cover */
.stApp::before {{
  content: "";
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.00);
  z-index: -1;
}}

.block-container {{
  padding-top: 2.25rem !important;
  max-width: 1400px !important;
}}

[data-testid="stSidebar"] {{
  display: none !important;
}}

/* ---------- TOP NAV ---------- */
.fca-nav {{
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
  padding: 0.85rem 1.0rem;
  border-radius: 18px;
  background: rgba(10, 16, 30, 0.55);
  border: 1px solid rgba(110, 160, 255, 0.20);
  box-shadow: 0 0 22px rgba(0, 140, 255, 0.08);
  backdrop-filter: blur(10px);
  margin-bottom: 1.25rem;
}}
.fca-nav .brand {{
  display:flex; align-items:center; gap:0.75rem;
}}
.fca-nav img {{
  width: 44px; height: 44px; border-radius: 12px;
  filter: drop-shadow(0 0 14px rgba(80,120,255,0.55));
}}
.fca-nav .brand-title {{
  font-weight: 900;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  text-shadow: 0 0 18px rgba(80,120,255,0.35);
}}
.fca-nav .navlinks {{
  display:flex; align-items:center; gap:0.6rem;
}}
.fca-pill {{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding: 0.60rem 1.0rem;
  border-radius: 999px;
  text-decoration: none !important;
  color: #e8ecff !important;
  background: rgba(15, 22, 40, 0.55);
  border: 1px solid rgba(110, 160, 255, 0.25);
  box-shadow: 0 0 18px rgba(0, 140, 255, 0.08);
  transition: 0.18s ease;
  font-weight: 700;
}}
.fca-pill:hover {{
  transform: translateY(-1px);
  border: 1px solid rgba(140, 190, 255, 0.45);
  box-shadow: 0 0 26px rgba(0, 170, 255, 0.18);
}}
.fca-pill.active {{
  color: #ffffff !important;
  border: 1px solid rgba(0, 212, 255, 0.45);
  box-shadow: 0 0 18px rgba(0, 212, 255, 0.22);
}}

/* ---------- HEADERS ---------- */
.fca-hero {{
  padding: 1.2rem 1.2rem;
  border-radius: 22px;
  background: rgba(10, 16, 30, 0.52);
  border: 1px solid rgba(110, 160, 255, 0.18);
  box-shadow: 0 0 30px rgba(0, 140, 255, 0.10);
  backdrop-filter: blur(12px);
  margin-bottom: 1.25rem;
}}
.fca-hero h1 {{
  margin: 0;
  font-size: 2.0rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  text-shadow: 0 0 22px rgba(80,120,255,0.45);
}}
.fca-hero .sub {{
  margin-top: 0.35rem;
  opacity: 0.92;
  font-weight: 600;
}}

/* ---------- CARD GRID ---------- */
.fca-grid {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.9rem;
}}
@media (max-width: 1100px) {{
  .fca-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 700px) {{
  .fca-grid {{ grid-template-columns: 1fr; }}
}}

/* ---------- LEAGUE CARDS ---------- */
.league-card {{
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 0.7rem;
  padding: 1.0rem 1.0rem;
  border-radius: 18px;
  text-decoration:none !important;
  color: #e8ecff !important;
  background: rgba(10, 16, 30, 0.62);
  border: 1px solid rgba(110, 160, 255, 0.22);
  box-shadow: 0 0 22px rgba(0,140,255,0.10);
  backdrop-filter: blur(12px);
  transition: 0.18s ease;
  font-weight: 900;
  letter-spacing: 0.08em;
}}
.league-card:hover {{
  transform: translateY(-2px);
  border: 1px solid rgba(140, 190, 255, 0.45);
  box-shadow: 0 0 34px rgba(0, 190, 255, 0.18);
}}
.league-icon {{
  width: 34px; height: 34px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  border-radius: 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
}}

/* ---------- GAME CARDS ---------- */
.game-card {{
  display:block;
  border-radius: 22px;
  text-decoration: none !important;
  color: #e8ecff !important;
  background: rgba(8, 14, 28, 0.64);
  border: 1px solid rgba(110, 160, 255, 0.22);
  box-shadow: 0 0 24px rgba(0, 140, 255, 0.10);
  backdrop-filter: blur(12px);
  padding: 0.95rem 1.05rem;
  transition: 0.18s ease;
}}
.game-card:hover {{
  transform: translateY(-2px);
  border: 1px solid rgba(140, 190, 255, 0.45);
  box-shadow: 0 0 34px rgba(0, 190, 255, 0.18);
}}

.game-top {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 0.75rem;
}}
.teamline {{
  display:flex;
  align-items:center;
  gap: 0.55rem;
  font-weight: 900;
  letter-spacing: 0.04em;
}}
.teamline img {{
  width: 28px;
  height: 28px;
  object-fit: contain;
  filter: drop-shadow(0 0 10px rgba(90,140,255,0.35));
}}
.meta {{
  opacity: 0.90;
  font-weight: 650;
  font-size: 0.92rem;
}}
.kpis {{
  margin-top: 0.65rem;
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.55rem;
}}
.kpi {{
  border-radius: 16px;
  padding: 0.55rem 0.65rem;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
}}
.kpi .lab {{
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.85;
}}
.kpi .val {{
  font-size: 1.05rem;
  font-weight: 900;
  margin-top: 0.1rem;
  text-shadow: 0 0 10px rgba(0, 200, 255, 0.18);
}}
.kpi.missing .val {{
  opacity: 0.50;
}}

/* ---------- TEAMRANKINGS BAR TABLE ---------- */
.tr-table {{
  width: 100%;
  border-radius: 22px;
  background: rgba(8, 14, 28, 0.64);
  border: 1px solid rgba(110, 160, 255, 0.18);
  box-shadow: 0 0 24px rgba(0, 140, 255, 0.10);
  backdrop-filter: blur(12px);
  padding: 0.85rem 1.05rem;
}}
.tr-row {{
  display:grid;
  grid-template-columns: 1.2fr 1.6fr 1.2fr;
  gap: 0.9rem;
  align-items:center;
  padding: 0.65rem 0.2rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}}
.tr-row:last-child {{
  border-bottom: none;
}}
.tr-stat {{
  text-align:center;
  opacity: 0.90;
  font-weight: 900;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  font-size: 0.80rem;
}}
.tr-val {{
  font-weight: 900;
  opacity: 0.95;
}}
.barwrap {{
  width: 100%;
  height: 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.08);
  overflow:hidden;
}}
.bar {{
  height: 100%;
  border-radius: 999px;
}}

/* ---------- ABOUT PAGE ---------- */
.about-shell {{
  max-width: 860px;
  margin: 0 auto;
}}
.page-title {{
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 800;
  letter-spacing: -0.03em;
  margin-bottom: 8px;
}}
.page-title .accent {{
  color: #00d4ff;
}}
.page-subtitle {{
  font-size: 15px;
  color: #a1a1aa;
  margin-bottom: 36px;
}}
.about-section {{
  margin-bottom: 34px;
}}
.about-section h2 {{
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}}
.about-section p {{
  font-size: 14px;
  color: #a1a1aa;
  line-height: 1.8;
  margin-bottom: 12px;
}}
.about-section ul {{
  list-style: none;
  padding: 0;
}}
.about-section li {{
  font-size: 14px;
  color: #a1a1aa;
  line-height: 1.8;
  padding-left: 20px;
  position: relative;
}}
.about-section li::before {{
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00d4ff;
}}
.about-card {{
  background: rgba(12, 18, 32, 0.90);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 22px;
  margin-bottom: 14px;
}}
.about-card h3 {{
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 8px;
}}
.about-card h3.props-accent {{
  color: #00d4ff;
}}
.about-card h3.game-accent {{
  color: #34d399;
}}
.about-card p {{
  font-size: 13px;
  color: #a1a1aa;
  line-height: 1.7;
  margin-bottom: 0;
}}
.faq-item {{
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 18px 0;
}}
.faq-item:last-child {{
  border-bottom: none;
}}
.faq-q {{
  font-size: 14px;
  font-weight: 600;
  color: #fafafa;
  margin-bottom: 8px;
}}
.faq-a {{
  font-size: 13px;
  color: #a1a1aa;
  line-height: 1.7;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


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


def apply_styles() -> None:
    inject_global_styles()

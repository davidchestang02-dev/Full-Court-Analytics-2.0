import streamlit as st

APP_CSS = """
<style>
/* --- Global --- */
html, body, [class*="css"]  {
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}

/* remove default padding */
.block-container { padding-top: 1.25rem; }

/* Hide Streamlit sidebar + hamburger */
[data-testid="stSidebar"] { display: none !important; }
button[kind="header"] { display: none !important; }

/* Header polish */
.app-title {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.2px;
  margin: 0 0 2px 0;
}
.app-subtitle {
  opacity: 0.75;
  margin: 0 0 12px 0;
}

/* Top nav */
.navbar {
  display: flex;
  gap: 10px;
  margin: 10px 0 18px 0;
}
.navpill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  font-size: 13px;
}
.navpill.active {
  border: 1px solid rgba(255,255,255,0.22);
  background: rgba(255,255,255,0.08);
}

/* Cards */
.card {
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.03);
  padding: 14px 14px;
}
.card:hover {
  border-color: rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.05);
}

/* Top plays grid cards */
.topplay-title {
  font-size: 14px;
  font-weight: 800;
  margin-bottom: 6px;
}
.muted { opacity: 0.75; font-size: 12px; }
.metric-row { display:flex; gap:12px; flex-wrap: wrap; margin-top: 10px; }
.metric-chip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
  font-size: 12px;
  font-weight: 700;
}

/* Table-like rows */
.row {
  display:flex;
  justify-content: space-between;
  align-items:center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
  margin-bottom: 8px;
}
.row:hover {
  border-color: rgba(255,255,255,0.16);
  background: rgba(255,255,255,0.05);
}
.row-left { display:flex; flex-direction: column; gap: 2px; }
.row-title { font-weight: 800; font-size: 14px; }
.row-sub { opacity: 0.75; font-size: 12px; }
.badge {
  font-size: 11px;
  font-weight: 800;
  padding: 5px 8px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
}

/* Stat compare bars */
.statgrid {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 12px;
  align-items: center;
}
.statname { opacity: 0.80; font-weight: 700; font-size: 12px; }
.statval { font-weight: 800; font-size: 12px; text-align: right; opacity: 0.90; }
.barwrap {
  height: 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
  display:flex;
}
.bar { height: 10px; }
.smallnote { opacity:0.7; font-size: 12px; margin-top: 6px; }
</style>
"""

def apply_styles():
    st.markdown(APP_CSS, unsafe_allow_html=True)

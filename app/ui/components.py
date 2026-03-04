from __future__ import annotations
import streamlit as st
from typing import Any, Dict, List, Optional


def metric_row(items: List[tuple]) -> None:
    cols = st.columns(len(items))
    for c, (label, value, help_text) in zip(cols, items):
        c.metric(label, value)
        if help_text:
            c.caption(help_text)


def edge_badge(x: Optional[float]) -> str:
    if x is None:
        return "—"
    # simple badge text; keep styling in CSS
    if x >= 3:
        return f"🟢 {x:+.2f}"
    if x >= 1:
        return f"🟡 {x:+.2f}"
    if x <= -3:
        return f"🔴 {x:+.2f}"
    if x <= -1:
        return f"🟠 {x:+.2f}"
    return f"{x:+.2f}"


def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

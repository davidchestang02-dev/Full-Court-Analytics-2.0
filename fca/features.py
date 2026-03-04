from __future__ import annotations

from typing import Any, Dict


def extract_features(game: Dict[str, Any]) -> Dict[str, Any]:
    """Return precomputed feature payload when available."""
    return (game or {}).get("features", {}) or {}

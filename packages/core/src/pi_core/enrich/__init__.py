"""Enrich thin GLPI resolutions before indexing (demo-quality runbooks)."""

from pi_core.enrich.resolutions import (
    SOLUCION_META_MAX,
    enrich_resolution,
    is_thin_resolution,
)

__all__ = [
    "SOLUCION_META_MAX",
    "enrich_resolution",
    "is_thin_resolution",
]

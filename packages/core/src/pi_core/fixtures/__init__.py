"""Demo fixtures (Kyocera cluster, etc.)."""

from pi_core.fixtures.kyocera_demo import (
    DEMO_ARTICLE_TEMPLATE,
    build_demo_articulo,
    ensure_clean_demo_articulo,
    load_kyocera_ticket_ids,
    reset_demo_state,
)

__all__ = [
    "DEMO_ARTICLE_TEMPLATE",
    "build_demo_articulo",
    "ensure_clean_demo_articulo",
    "load_kyocera_ticket_ids",
    "reset_demo_state",
]

"""Configuración expuesta al frontend (feature flags, ADR-0011)."""

from fastapi import APIRouter

from pi_core.feature_flags import get_flags

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/features", response_model=dict[str, bool])
async def features() -> dict[str, bool]:
    """Estado de los feature flags funcionales; la UI los usa para mostrar u ocultar capacidades."""
    return get_flags().model_dump()

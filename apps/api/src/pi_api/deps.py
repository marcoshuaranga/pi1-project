"""Shared API dependencies (process-wide singletons)."""

from functools import lru_cache

from fastapi import HTTPException

from pi_core.agents.orchestrator.graph import Orchestrator
from pi_core.feature_flags import flag_enabled
from pi_core.storage.kedb_store.store import KedbStore


def ensure_feature(name: str) -> None:
    """404 `feature_deshabilitada` si el flag está apagado (se evalúa en cada request)."""
    if not flag_enabled(name):
        raise HTTPException(status_code=404, detail="feature_deshabilitada")


def require_feature(name: str):
    """Dependencia de FastAPI: `dependencies=[Depends(require_feature("e05_..."))]`."""
    flag_enabled(name)  # falla temprano (al definir la ruta) si el nombre no existe

    def _guard() -> None:
        ensure_feature(name)

    return _guard


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


@lru_cache
def get_kedb_store() -> KedbStore:
    return KedbStore()

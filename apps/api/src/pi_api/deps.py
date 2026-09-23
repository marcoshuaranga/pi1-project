"""Shared API dependencies (process-wide singletons)."""

from functools import lru_cache

from pi_core.agents.orchestrator.graph import Orchestrator
from pi_core.storage.kedb_store.store import KedbStore


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


@lru_cache
def get_kedb_store() -> KedbStore:
    return KedbStore()

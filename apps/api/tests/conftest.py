"""Shared API test fixtures for contract-level endpoint checks."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app


@pytest.fixture
def api_client() -> TestClient:
    """Create an API client without sharing application state between tests."""
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def store_aislado(monkeypatch, tmp_path):
    """KedbStore propio por test, inyectado en los routers de tickets y en la sesión de tickets."""
    from pi_core.config import Settings
    from pi_core.storage.kedb_store.store import KedbStore

    store = KedbStore(
        Settings(kedb_db_path=str(tmp_path / "kedb.db"), kedb_docs_path=str(tmp_path / "articles"))
    )
    monkeypatch.setattr("pi_api.routers.tickets.get_kedb_store", lambda: store)
    monkeypatch.setattr("pi_api.state.get_kedb_store", lambda: store)
    return store

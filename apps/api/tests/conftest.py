"""Shared API test fixtures for contract-level endpoint checks."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app


@pytest.fixture
def api_client() -> TestClient:
    """Create an API client without sharing application state between tests."""
    with TestClient(create_app()) as client:
        yield client

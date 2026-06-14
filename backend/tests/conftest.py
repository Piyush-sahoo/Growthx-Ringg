"""Shared test fixtures."""

import pytest

from app.store import InMemoryRepository, store


@pytest.fixture(autouse=True)
def _reset_store():
    """Reset the in-memory repository between tests for isolation."""
    if isinstance(store, InMemoryRepository):
        store._calls.clear()
        store._seen.clear()
    yield

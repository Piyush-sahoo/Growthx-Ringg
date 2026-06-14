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


@pytest.fixture(autouse=True)
def _fake_tools(request, monkeypatch):
    """Stub the real tool senders for behavioral tests.

    Integration tests (marked `integration`) keep the real implementations so they
    actually hit Resend/Twilio.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return

    async def _fake_email(**kwargs):
        return {"id": "fake-email-id"}

    async def _fake_whatsapp(**kwargs):
        return {"sid": "fake-wa-sid"}

    monkeypatch.setattr("app.tools.send_email", _fake_email)
    monkeypatch.setattr("app.tools.send_whatsapp", _fake_whatsapp)
    yield

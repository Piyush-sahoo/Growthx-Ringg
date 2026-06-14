"""Shared test fixtures."""

import pytest

from app.store import InMemoryRepository, store


@pytest.fixture(autouse=True)
def _reset_store():
    """Reset the in-memory repository between tests for isolation."""
    if isinstance(store, InMemoryRepository):
        store._calls.clear()
        store._seen.clear()
        store._workflows.clear()
        store._contacts.clear()
    yield


@pytest.fixture(autouse=True)
def _fake_externals(request, monkeypatch):
    """Stub real outbound senders/dialers for behavioral tests.

    Integration tests (marked `integration`) keep the real implementations.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return

    async def _fake_email(**kwargs):
        return {"id": "fake-email-id"}

    async def _fake_whatsapp(**kwargs):
        return {"sid": "fake-wa-sid"}

    async def _fake_call(**kwargs):
        return {"call_id": "fake-followup-call-id"}

    async def _fake_video(**kwargs):
        return {"id": "fake-video"}

    monkeypatch.setattr("app.tools.send_email", _fake_email)
    monkeypatch.setattr("app.tools.send_whatsapp", _fake_whatsapp)
    monkeypatch.setattr("app.tools.send_recap_video", _fake_video)
    # Used by follow-up scheduling so behavioral tests never place a real call.
    monkeypatch.setattr("app.ringg.ringg_client.place_outbound_call", _fake_call)

    # Force tools "configured" so branch behavior is deterministic regardless of
    # whether keys are present in the environment (e.g. CI has no .env).
    monkeypatch.setattr("app.tools.email_configured", lambda: True)
    monkeypatch.setattr("app.tools.whatsapp_configured", lambda: True)
    monkeypatch.setattr("app.tools.video_configured", lambda: True)
    yield

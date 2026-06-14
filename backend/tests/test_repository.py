"""Exercises the MongoRepository code path against an in-memory Mongo (mongomock)."""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.models import CallRecord, CallStatus
from app.store import MongoRepository


@pytest.fixture
async def repo():
    r = MongoRepository("mongodb://mock", "flowforge_test")
    client = AsyncMongoMockClient()
    db = client["flowforge_test"]
    r._client = client
    r._calls = db["calls"]
    r._events = db["events"]
    await r._events.create_index("key", unique=True)
    return r


async def test_add_get_list_update(repo):
    rec = CallRecord(customer_name="Asha", phone_number="+919812345678", ringg_call_id="rc-1")
    await repo.add(rec)

    got = await repo.get(rec.id)
    assert got is not None and got.customer_name == "Asha"

    by_ringg = await repo.get_by_ringg_id("rc-1")
    assert by_ringg is not None and by_ringg.id == rec.id

    rec.status = CallStatus.completed
    rec.transcript = "bot: hi\nuser: bye"
    rec.outcome = "activated_distracted"
    await repo.update(rec)

    again = await repo.get(rec.id)
    assert again.status == CallStatus.completed
    assert again.transcript == "bot: hi\nuser: bye"
    assert again.outcome == "activated_distracted"

    listed = await repo.list()
    assert any(r.id == rec.id for r in listed)


async def test_seen_event_dedupe(repo):
    assert await repo.seen_event("c1", "all_processing_completed") is False
    # Same key → already processed.
    assert await repo.seen_event("c1", "all_processing_completed") is True
    # Different event type for same call is independent.
    assert await repo.seen_event("c1", "call_completed") is False

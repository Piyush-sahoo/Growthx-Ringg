"""Async repository for call/run records (Context Objects).

Backed by MongoDB (Motor) when ``MONGODB_URI`` is set; otherwise an in-memory
implementation so dev and tests run without a database. Both implementations
share the same async interface and an event-dedupe registry keyed by
``call_id + event_type`` (Ringg retries webhooks).
"""

from __future__ import annotations

from asyncio import Lock

from .config import get_settings
from .models import CallRecord, ContextObject


class InMemoryRepository:
    """Process-local async store. Used in dev/tests (no MONGODB_URI)."""

    def __init__(self) -> None:
        self._calls: dict[str, CallRecord] = {}
        self._seen: set[str] = set()
        self._workflows: dict[str, dict] = {}
        self._contacts: dict[str, ContextObject] = {}
        self._lock = Lock()

    async def connect(self) -> None:  # no-op
        return None

    async def save_workflow(self, graph: dict) -> dict:
        async with self._lock:
            self._workflows[graph["id"]] = graph
        return graph

    async def get_workflow(self, workflow_id: str) -> dict | None:
        return self._workflows.get(workflow_id)

    async def list_workflows(self) -> list[dict]:
        return list(self._workflows.values())

    async def get_contact(self, phone_number: str) -> ContextObject | None:
        return self._contacts.get(phone_number)

    async def save_contact(self, contact: ContextObject) -> ContextObject:
        async with self._lock:
            self._contacts[contact.phone_number] = contact
        return contact

    async def close(self) -> None:  # no-op
        return None

    async def add(self, record: CallRecord) -> CallRecord:
        async with self._lock:
            self._calls[record.id] = record
        return record

    async def get(self, call_id: str) -> CallRecord | None:
        return self._calls.get(call_id)

    async def get_by_ringg_id(self, ringg_call_id: str) -> CallRecord | None:
        for r in self._calls.values():
            if r.ringg_call_id and r.ringg_call_id == ringg_call_id:
                return r
        return None

    async def list(self) -> list[CallRecord]:
        return sorted(self._calls.values(), key=lambda r: r.created_at, reverse=True)

    async def update(self, record: CallRecord) -> CallRecord:
        async with self._lock:
            self._calls[record.id] = record
        return record

    async def seen_event(self, call_id: str, event_type: str) -> bool:
        """Return True if this (call_id, event_type) was already processed."""
        key = f"{call_id}:{event_type}"
        async with self._lock:
            if key in self._seen:
                return True
            self._seen.add(key)
            return False


class MongoRepository:
    """MongoDB-backed store (Motor). Documents keyed by record.id."""

    def __init__(self, uri: str, db_name: str) -> None:
        self._uri = uri
        self._db_name = db_name
        self._client = None
        self._calls = None
        self._events = None
        self._workflows = None
        self._contacts = None

    async def connect(self) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        self._client = AsyncIOMotorClient(self._uri)
        db = self._client[self._db_name]
        self._calls = db["calls"]
        self._events = db["events"]
        self._workflows = db["workflows"]
        self._contacts = db["contacts"]
        # Unique index gives us atomic dedupe via duplicate-key errors.
        await self._events.create_index("key", unique=True)
        await self._calls.create_index("ringg_call_id")

    async def save_workflow(self, graph: dict) -> dict:
        doc = {**graph, "_id": graph["id"]}
        await self._workflows.replace_one({"_id": graph["id"]}, doc, upsert=True)
        return graph

    async def get_workflow(self, workflow_id: str) -> dict | None:
        doc = await self._workflows.find_one({"_id": workflow_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def list_workflows(self) -> list[dict]:
        out = []
        async for d in self._workflows.find():
            d.pop("_id", None)
            out.append(d)
        return out

    async def get_contact(self, phone_number: str) -> ContextObject | None:
        doc = await self._contacts.find_one({"_id": phone_number})
        return ContextObject(**doc) if doc else None

    async def save_contact(self, contact: ContextObject) -> ContextObject:
        doc = {**contact.model_dump(mode="json"), "_id": contact.phone_number}
        await self._contacts.replace_one({"_id": contact.phone_number}, doc, upsert=True)
        return contact

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()

    @staticmethod
    def _doc(record: CallRecord) -> dict:
        d = record.model_dump(mode="json")
        d["_id"] = record.id
        return d

    async def add(self, record: CallRecord) -> CallRecord:
        await self._calls.replace_one({"_id": record.id}, self._doc(record), upsert=True)
        return record

    async def get(self, call_id: str) -> CallRecord | None:
        doc = await self._calls.find_one({"_id": call_id})
        return CallRecord(**doc) if doc else None

    async def get_by_ringg_id(self, ringg_call_id: str) -> CallRecord | None:
        doc = await self._calls.find_one({"ringg_call_id": ringg_call_id})
        return CallRecord(**doc) if doc else None

    async def list(self) -> list[CallRecord]:
        cursor = self._calls.find().sort("created_at", -1)
        return [CallRecord(**d) async for d in cursor]

    async def update(self, record: CallRecord) -> CallRecord:
        await self._calls.replace_one({"_id": record.id}, self._doc(record), upsert=True)
        return record

    async def seen_event(self, call_id: str, event_type: str) -> bool:
        from pymongo.errors import DuplicateKeyError

        try:
            await self._events.insert_one({"key": f"{call_id}:{event_type}"})
            return False
        except DuplicateKeyError:
            return True


def _build_repository():
    settings = get_settings()
    if settings.mongodb_uri:
        return MongoRepository(settings.mongodb_uri, settings.mongodb_db)
    return InMemoryRepository()


# Singleton repository shared across the app. `connect()` is called on startup.
store = _build_repository()

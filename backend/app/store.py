"""In-memory call store.

Hackathon-grade persistence: a process-local dict. Swap for Supabase/Postgres
later by keeping the same method signatures. Thread-safe via a simple lock.
"""

from threading import Lock

from .models import CallRecord


class CallStore:
    def __init__(self) -> None:
        self._calls: dict[str, CallRecord] = {}
        self._lock = Lock()

    def add(self, record: CallRecord) -> CallRecord:
        with self._lock:
            self._calls[record.id] = record
        return record

    def get(self, call_id: str) -> CallRecord | None:
        return self._calls.get(call_id)

    def get_by_ringg_id(self, ringg_call_id: str) -> CallRecord | None:
        for record in self._calls.values():
            if record.ringg_call_id and record.ringg_call_id == ringg_call_id:
                return record
        return None

    def list(self) -> list[CallRecord]:
        return sorted(self._calls.values(), key=lambda r: r.created_at, reverse=True)

    def update(self, record: CallRecord) -> CallRecord:
        with self._lock:
            self._calls[record.id] = record
        return record


# Singleton store shared across the app.
store = CallStore()

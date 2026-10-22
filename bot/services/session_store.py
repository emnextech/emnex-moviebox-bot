from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from uuid import uuid4


@dataclass(slots=True)
class SessionEntry:
    payload: object
    expires_at: float


class SessionStore:
    def __init__(self, *, default_ttl_seconds: int = 900) -> None:
        self._default_ttl_seconds = default_ttl_seconds
        self._entries: dict[str, SessionEntry] = {}

    def put(self, payload: object, *, ttl_seconds: int | None = None) -> str:
        self._purge_expired()
        token = uuid4().hex[:10]
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        self._entries[token] = SessionEntry(payload=payload, expires_at=monotonic() + max(ttl, 60))
        return token

    def get(self, token: str) -> object | None:
        if not token:
            return None
        self._purge_expired()
        entry = self._entries.get(token)
        if entry is None or entry.expires_at <= monotonic():
            self._entries.pop(token, None)
            return None
        return entry.payload

    def replace(self, token: str, payload: object, *, ttl_seconds: int | None = None) -> bool:
        if token not in self._entries:
            return False
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        self._entries[token] = SessionEntry(payload=payload, expires_at=monotonic() + max(ttl, 60))
        return True

    def _purge_expired(self) -> None:
        now = monotonic()
        expired = [token for token, entry in self._entries.items() if entry.expires_at <= now]
        for token in expired:
            self._entries.pop(token, None)

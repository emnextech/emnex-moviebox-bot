from __future__ import annotations

import time

from bot.config.settings import Settings


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self._cooldowns = {
            "search": settings.search_cooldown_seconds,
            "detail": settings.source_cooldown_seconds,
            "source": settings.source_cooldown_seconds,
            "bulk": settings.bulk_cooldown_seconds,
        }
        self._timestamps: dict[tuple[int, str], float] = {}

    def check(self, user_id: int, action: str) -> tuple[bool, int]:
        now = time.monotonic()
        key = (user_id, action)
        cooldown = max(int(self._cooldowns.get(action, 0)), 0)
        if cooldown == 0:
            self._timestamps[key] = now
            return True, 0

        last_seen = self._timestamps.get(key)
        if last_seen is None:
            self._timestamps[key] = now
            return True, 0

        elapsed = now - last_seen
        if elapsed >= cooldown:
            self._timestamps[key] = now
            return True, 0

        retry_after = max(1, int(cooldown - elapsed + 0.999))
        return False, retry_after

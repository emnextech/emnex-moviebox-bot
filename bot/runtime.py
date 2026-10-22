from __future__ import annotations

from dataclasses import dataclass

from bot.config.settings import Settings
from bot.services import RateLimiter, SessionStore, UserService, WorkerApiClient


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    api_client: WorkerApiClient
    user_service: UserService
    rate_limiter: RateLimiter
    session_store: SessionStore

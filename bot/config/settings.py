from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("bot/.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    worker_api_base: str = Field(alias="WORKER_API_BASE")
    worker_api_key: str = Field(alias="WORKER_API_KEY")
    site_base_url: str = Field(alias="SITE_BASE_URL")
    miniapp_url: str = Field(default="", alias="MINIAPP_URL")
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    bot_owner_ids: Annotated[tuple[int, ...], NoDecode] = Field(default_factory=tuple, alias="BOT_OWNER_IDS")

    bot_name: str = Field(default="EmnexMovies Bot", alias="BOT_NAME")
    brand_name: str = Field(default="EmnexMovies", alias="BRAND_NAME")
    support_contact: str = Field(default="@emnexmovies", alias="SUPPORT_CONTACT")
    pro_monthly_price_usd: float = Field(default=2.99, alias="PRO_MONTHLY_PRICE_USD")
    pro_whatsapp_url: str = Field(default="https://wa.me/260950628680", alias="PRO_WHATSAPP_URL")
    pro_telegram_url: str = Field(default="https://t.me/Emnnex", alias="PRO_TELEGRAM_URL")
    max_bulk_episodes: int = Field(default=10, alias="MAX_BULK_EPISODES")
    max_search_results: int = Field(default=8, alias="MAX_SEARCH_RESULTS")
    search_cooldown_seconds: int = Field(default=3, alias="SEARCH_COOLDOWN_SECONDS")
    source_cooldown_seconds: int = Field(default=2, alias="SOURCE_COOLDOWN_SECONDS")
    bulk_cooldown_seconds: int = Field(default=10, alias="BULK_COOLDOWN_SECONDS")
    source_concurrency: int = Field(default=3, alias="SOURCE_CONCURRENCY")
    worker_timeout_seconds: float = Field(default=20.0, alias="WORKER_TIMEOUT_SECONDS")

    @field_validator("worker_api_base", "site_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("bot_owner_ids", mode="before")
    @classmethod
    def parse_owner_ids(cls, value: object) -> tuple[int, ...]:
        if value is None or value == "":
            return ()
        if isinstance(value, (list, tuple, set)):
            return tuple(int(item) for item in value)
        raw = str(value)
        return tuple(int(part.strip()) for part in raw.split(",") if part.strip())

    def is_owner(self, user_id: int) -> bool:
        return user_id in self.bot_owner_ids

    @property
    def pro_price_label(self) -> str:
        return f"${self.pro_monthly_price_usd:.2f}/month"

    @property
    def web_app_url(self) -> str:
        return (self.miniapp_url or self.site_base_url).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

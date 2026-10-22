from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from aiogram.types import User as TelegramUser
from supabase import Client, create_client

from bot.config.settings import Settings
from bot.models import TelegramUserRecord, UserPlan, utc_now


@dataclass(slots=True)
class BotStats:
    total_users: int
    active_pro_users: int
    events_last_24h: int


class UserService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Supabase is optional. When creds are absent (e.g. local testing), we
        # fall back to an in-memory store so search/stream/download still work;
        # user rows and events simply aren't persisted.
        self._memory: dict[int, TelegramUserRecord] | None
        if settings.supabase_url and settings.supabase_service_role_key:
            self._client: Client | None = create_client(
                settings.supabase_url, settings.supabase_service_role_key
            )
            self._memory = None
        else:
            self._client = None
            self._memory = {}

    async def ensure_user(self, user: TelegramUser) -> TelegramUserRecord:
        return await asyncio.to_thread(self._ensure_user_sync, user)

    async def grant_pro(self, telegram_user_id: int, days: int) -> TelegramUserRecord:
        return await asyncio.to_thread(self._grant_pro_sync, telegram_user_id, days)

    async def revoke(self, telegram_user_id: int) -> TelegramUserRecord | None:
        return await asyncio.to_thread(self._revoke_sync, telegram_user_id)

    async def get_user(self, telegram_user_id: int) -> TelegramUserRecord | None:
        return await asyncio.to_thread(self._get_user_sync, telegram_user_id)

    async def get_stats(self) -> BotStats:
        return await asyncio.to_thread(self._get_stats_sync)

    async def log_event(
        self,
        *,
        telegram_user_id: int,
        action: str,
        outcome: str,
        plan_at_time: UserPlan,
        subject_id: str | None = None,
        subject_type: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        quality: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._log_event_sync,
            telegram_user_id,
            action,
            outcome,
            plan_at_time,
            subject_id,
            subject_type,
            season,
            episode,
            quality,
            metadata or {},
        )

    def _ensure_user_sync(self, user: TelegramUser) -> TelegramUserRecord:
        if self._memory is not None:
            now = utc_now()
            record = self._memory.get(user.id)
            if record is None:
                record = TelegramUserRecord(
                    telegram_user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    plan=UserPlan.PRO,
                    created_at=now,
                )
            record.username = user.username
            record.first_name = user.first_name
            record.last_name = user.last_name
            record.last_seen_at = now
            record.updated_at = now
            self._memory[user.id] = record
            return record

        existing = self._get_user_sync(user.id)
        now = utc_now()
        if existing is None:
            row = {
                "telegram_user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "plan": UserPlan.BASIC.value,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "last_seen_at": now.isoformat(),
            }
            response = self._client.table("telegram_users").insert(row).execute()
            return TelegramUserRecord.from_row(response.data[0])

        updates = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "last_seen_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if existing.plan == UserPlan.PRO and existing.active_plan == UserPlan.BASIC:
            updates["plan"] = UserPlan.BASIC.value
            updates["plan_expires_at"] = None

        response = (
            self._client.table("telegram_users")
            .update(updates)
            .eq("telegram_user_id", user.id)
            .execute()
        )
        rows = response.data or []
        return TelegramUserRecord.from_row(rows[0]) if rows else self._get_user_sync(user.id)  # pragma: no cover

    def _grant_pro_sync(self, telegram_user_id: int, days: int) -> TelegramUserRecord:
        expires_at = utc_now() + timedelta(days=days)
        if self._memory is not None:
            record = self._memory.get(telegram_user_id) or TelegramUserRecord(
                telegram_user_id=telegram_user_id, created_at=utc_now()
            )
            record.plan = UserPlan.PRO
            record.plan_expires_at = expires_at
            record.updated_at = utc_now()
            self._memory[telegram_user_id] = record
            return record

        existing = self._get_user_sync(telegram_user_id)
        updates = {
            "plan": UserPlan.PRO.value,
            "plan_expires_at": expires_at.isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        if existing is None:
            updates["telegram_user_id"] = telegram_user_id
            updates["created_at"] = utc_now().isoformat()
            updates["last_seen_at"] = utc_now().isoformat()
            response = self._client.table("telegram_users").insert(updates).execute()
            return TelegramUserRecord.from_row(response.data[0])

        response = (
            self._client.table("telegram_users")
            .update(updates)
            .eq("telegram_user_id", telegram_user_id)
            .execute()
        )
        return TelegramUserRecord.from_row(response.data[0])

    def _revoke_sync(self, telegram_user_id: int) -> TelegramUserRecord | None:
        if self._memory is not None:
            record = self._memory.get(telegram_user_id)
            if record is None:
                return None
            record.plan = UserPlan.BASIC
            record.plan_expires_at = None
            record.updated_at = utc_now()
            self._memory[telegram_user_id] = record
            return record

        existing = self._get_user_sync(telegram_user_id)
        if existing is None:
            return None
        response = (
            self._client.table("telegram_users")
            .update(
                {
                    "plan": UserPlan.BASIC.value,
                    "plan_expires_at": None,
                    "updated_at": utc_now().isoformat(),
                }
            )
            .eq("telegram_user_id", telegram_user_id)
            .execute()
        )
        return TelegramUserRecord.from_row(response.data[0])

    def _get_user_sync(self, telegram_user_id: int) -> TelegramUserRecord | None:
        if self._memory is not None:
            return self._memory.get(telegram_user_id)

        response = (
            self._client.table("telegram_users")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        user = TelegramUserRecord.from_row(rows[0])
        if user.plan == UserPlan.PRO and user.active_plan == UserPlan.BASIC:
            response = (
                self._client.table("telegram_users")
                .update(
                    {
                        "plan": UserPlan.BASIC.value,
                        "plan_expires_at": None,
                        "updated_at": utc_now().isoformat(),
                    }
                )
                .eq("telegram_user_id", telegram_user_id)
                .execute()
            )
            rows = response.data or rows
            user = TelegramUserRecord.from_row(rows[0])
        return user

    def _get_stats_sync(self) -> BotStats:
        if self._memory is not None:
            users = list(self._memory.values())
            now = utc_now()
            pro = sum(
                1
                for u in users
                if u.plan == UserPlan.PRO and (u.plan_expires_at is None or u.plan_expires_at > now)
            )
            return BotStats(total_users=len(users), active_pro_users=pro, events_last_24h=0)

        now_iso = utc_now().isoformat()
        yesterday_iso = (utc_now() - timedelta(hours=24)).isoformat()

        total_response = self._client.table("telegram_users").select("telegram_user_id", count="exact").limit(1).execute()
        pro_response = (
            self._client.table("telegram_users")
            .select("telegram_user_id", count="exact")
            .eq("plan", UserPlan.PRO.value)
            .gt("plan_expires_at", now_iso)
            .limit(1)
            .execute()
        )
        event_response = (
            self._client.table("telegram_events")
            .select("id", count="exact")
            .gte("created_at", yesterday_iso)
            .limit(1)
            .execute()
        )

        return BotStats(
            total_users=total_response.count or 0,
            active_pro_users=pro_response.count or 0,
            events_last_24h=event_response.count or 0,
        )

    def _log_event_sync(
        self,
        telegram_user_id: int,
        action: str,
        outcome: str,
        plan_at_time: UserPlan,
        subject_id: str | None,
        subject_type: str | None,
        season: int | None,
        episode: int | None,
        quality: str | None,
        metadata: dict[str, Any],
    ) -> None:
        if self._memory is not None:
            return  # events not persisted in local in-memory mode

        row = {
            "telegram_user_id": telegram_user_id,
            "action": action,
            "outcome": outcome,
            "plan_at_time": plan_at_time.value,
            "subject_id": subject_id,
            "subject_type": subject_type,
            "season": season,
            "episode": episode,
            "quality": quality,
            "metadata": metadata,
            "created_at": utc_now().isoformat(),
        }
        self._client.table("telegram_events").insert(row).execute()

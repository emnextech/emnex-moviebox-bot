from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.runtime import ServiceContainer
from bot.utils.formatter import format_admin_stats, format_admin_user

router = Router(name="admin_commands")


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


def _ensure_owner(message: Message, services: ServiceContainer) -> bool:
    return bool(message.from_user and services.settings.is_owner(message.from_user.id))


async def _ensure_admin_access(message: Message, services: ServiceContainer) -> bool:
    if not _is_private(message):
        await message.answer("Owner commands only work in private chat.")
        return False
    if not _ensure_owner(message, services):
        await message.answer("This command is owner-only.")
        return False
    return True


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject, services: ServiceContainer) -> None:
    if not await _ensure_admin_access(message, services):
        return

    actor = await services.user_service.ensure_user(message.from_user)
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer("Usage: /grant <user_id> <days>")
        return

    try:
        target_user_id, days = int(parts[0]), int(parts[1])
    except ValueError:
        await message.answer("Usage: /grant <user_id> <days>")
        return

    if days <= 0:
        await message.answer("Days must be greater than zero.")
        return

    updated = await services.user_service.grant_pro(target_user_id, days)
    await services.user_service.log_event(
        telegram_user_id=actor.telegram_user_id,
        action="admin_grant",
        outcome="success",
        plan_at_time=actor.active_plan,
        metadata={"target_user_id": target_user_id, "days": days},
    )
    await message.answer(f"Granted PRO to <code>{target_user_id}</code> for {days} days.\n\n{format_admin_user(updated)}")


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, command: CommandObject, services: ServiceContainer) -> None:
    if not await _ensure_admin_access(message, services):
        return

    actor = await services.user_service.ensure_user(message.from_user)
    args = (command.args or "").strip()
    if not args:
        await message.answer("Usage: /revoke <user_id>")
        return

    try:
        target_user_id = int(args)
    except ValueError:
        await message.answer("Usage: /revoke <user_id>")
        return

    revoked = await services.user_service.revoke(target_user_id)
    await services.user_service.log_event(
        telegram_user_id=actor.telegram_user_id,
        action="admin_revoke",
        outcome="success" if revoked else "missing",
        plan_at_time=actor.active_plan,
        metadata={"target_user_id": target_user_id},
    )
    await message.answer(format_admin_user(revoked))


@router.message(Command("user"))
async def cmd_user(message: Message, command: CommandObject, services: ServiceContainer) -> None:
    if not await _ensure_admin_access(message, services):
        return

    await services.user_service.ensure_user(message.from_user)
    args = (command.args or "").strip()
    if not args:
        await message.answer("Usage: /user <user_id>")
        return

    try:
        target_user_id = int(args)
    except ValueError:
        await message.answer("Usage: /user <user_id>")
        return

    user = await services.user_service.get_user(target_user_id)
    await message.answer(format_admin_user(user))


@router.message(Command("stats"))
async def cmd_stats(message: Message, services: ServiceContainer) -> None:
    if not await _ensure_admin_access(message, services):
        return

    await services.user_service.ensure_user(message.from_user)
    stats = await services.user_service.get_stats()
    await message.answer(format_admin_stats(stats))

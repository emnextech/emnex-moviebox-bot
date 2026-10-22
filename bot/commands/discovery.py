from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers.discovery_handler import send_browse_chooser, send_home_sections
from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.formatter import format_error

router = Router(name="discovery_commands")


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


@router.message(Command(commands=["discover", "home"]))
async def cmd_discover(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    user = await services.user_service.ensure_user(message.from_user)
    try:
        await send_home_sections(message, user.telegram_user_id, services)
    except ApiError as exc:
        await message.answer(format_error(exc.message))


@router.message(Command("browse"))
async def cmd_browse(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    await services.user_service.ensure_user(message.from_user)
    await send_browse_chooser(message)

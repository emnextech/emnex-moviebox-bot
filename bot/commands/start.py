from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from bot.runtime import ServiceContainer
from bot.utils.buttons import support_contact_keyboard
from bot.utils.formatter import format_help, format_plan, format_pro_pitch, format_welcome

router = Router(name="start_commands")


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


def _open_app_keyboard(services: ServiceContainer) -> InlineKeyboardMarkup:
    url = services.settings.web_app_url
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎬 Open EmnexMovies", web_app=WebAppInfo(url=url))]]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    await services.user_service.ensure_user(message.from_user)
    await message.answer(format_welcome(services.settings), reply_markup=_open_app_keyboard(services))


@router.message(Command("help"))
async def cmd_help(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    await services.user_service.ensure_user(message.from_user)
    await message.answer(format_help(services.settings))


@router.message(Command("plan"))
async def cmd_plan(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    user = await services.user_service.ensure_user(message.from_user)
    await message.answer(format_plan(user, services.settings), reply_markup=support_contact_keyboard(services.settings))


@router.message(Command("pro"))
async def cmd_pro(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    user = await services.user_service.ensure_user(message.from_user)
    await services.user_service.log_event(
        telegram_user_id=user.telegram_user_id,
        action="view_pro_pitch",
        outcome="shown",
        plan_at_time=user.active_plan,
    )
    await message.answer(format_pro_pitch(services.settings), reply_markup=support_contact_keyboard(services.settings))

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from html import escape

from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.buttons import search_results_keyboard
from bot.utils.callbacks import MediaSelectCallback
from bot.utils.formatter import format_error, format_search_results

router = Router(name="search_commands")


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


async def _run_search(message: Message, query: str, services: ServiceContainer) -> None:
    user = await services.user_service.ensure_user(message.from_user)
    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "search")
    if not allowed:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="search",
            outcome="rate_limited",
            plan_at_time=user.active_plan,
            metadata={"retry_after": retry_after, "query": query},
        )
        await message.answer(f"Slow down a little. Try searching again in {retry_after}s.")
        return

    try:
        results = await services.api_client.search(query)
    except ApiError as exc:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="search",
            outcome="error",
            plan_at_time=user.active_plan,
            metadata={"query": query, "message": exc.message},
        )
        await message.answer(format_error(exc.message))
        return

    trimmed = results[: services.settings.max_search_results]
    if not trimmed:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="search",
            outcome="empty",
            plan_at_time=user.active_plan,
            metadata={"query": query},
        )
        await message.answer(f"No matches found for <b>{escape(query)}</b>. Try a different title.")
        return

    await services.user_service.log_event(
        telegram_user_id=user.telegram_user_id,
        action="search",
        outcome="success",
        plan_at_time=user.active_plan,
        metadata={"query": query, "results": len(trimmed)},
    )
    origin = "search"

    def callback_for(item) -> str:
        ref = services.session_store.put(
            {
                "owner_id": user.telegram_user_id,
                "poster": item.poster,
                "origin": origin,
            }
        )
        return MediaSelectCallback(subject_id=item.subject_id, ref=ref).pack()

    await message.answer(
        format_search_results(query, trimmed, len(results)),
        reply_markup=search_results_keyboard(trimmed, callback_for=callback_for),
    )


@router.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    query = (command.args or "").strip()
    if not query:
        await message.answer("Use /search followed by a movie or TV title.")
        return
    await _run_search(message, query, services)


@router.message(F.text & ~F.text.startswith("/"))
async def text_search(message: Message, services: ServiceContainer) -> None:
    if not _is_private(message):
        return
    query = (message.text or "").strip()
    if not query:
        return
    await _run_search(message, query, services)

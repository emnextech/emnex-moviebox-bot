from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.buttons import movie_quality_keyboard, season_keyboard
from bot.utils.callbacks import MediaSelectCallback
from bot.utils.formatter import format_media_details

from .helpers import answer_callback_error, edit_callback_message, unique_variants

router = Router(name="movie_handler")


def _is_private(query: CallbackQuery) -> bool:
    return bool(query.message and query.message.chat.type == "private")


@router.callback_query(MediaSelectCallback.filter())
async def on_media_selected(
    query: CallbackQuery,
    callback_data: MediaSelectCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "detail")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        ref_payload = services.session_store.get(callback_data.ref) if callback_data.ref else None
        poster_url = media.poster
        if isinstance(ref_payload, dict):
            poster_url = str(ref_payload.get("poster") or poster_url)

        if media.is_movie:
            sources = await services.api_client.get_sources(media.subject_id)
            keyboard = movie_quality_keyboard(
                settings=services.settings,
                plan=user.active_plan,
                media=media,
                sources=unique_variants(sources),
            )
        else:
            keyboard = season_keyboard(media)

        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="open_media",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type=media.media_label.lower(),
            metadata={"is_movie": media.is_movie},
        )
        await edit_callback_message(
            query,
            format_media_details(media, user.active_plan),
            reply_markup=keyboard,
            poster_url=poster_url,
        )
        await query.answer()
    except ApiError as exc:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="open_media",
            outcome="error",
            plan_at_time=user.active_plan,
            subject_id=callback_data.subject_id,
            metadata={"message": exc.message},
        )
        await answer_callback_error(query, exc)

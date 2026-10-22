from __future__ import annotations

from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.config.settings import Settings
from bot.models import MediaDetails, SeasonInfo, SourceOption
from bot.services import ApiError
from bot.utils.formatter import format_error


def season_info_for(media: MediaDetails, season: int) -> SeasonInfo | None:
    for item in media.seasons:
        if item.season_number == season:
            return item
    return None


def page_bounds(settings: Settings, page: int, max_episode: int) -> tuple[int, int]:
    start = page * settings.max_bulk_episodes + 1
    end = min(max_episode, start + settings.max_bulk_episodes - 1)
    return start, end


def unique_variants(sources: list[SourceOption]) -> list[SourceOption]:
    seen: set[str] = set()
    unique: list[SourceOption] = []
    for source in sorted(sources, key=lambda item: (-item.quality_num, item.display_label.lower())):
        if source.variant_id in seen:
            continue
        seen.add(source.variant_id)
        unique.append(source)
    return unique


def sources_for_variant(sources: list[SourceOption], variant_id: str) -> list[SourceOption]:
    return [source for source in sources if source.variant_id == variant_id]


def readable_api_error(exc: ApiError) -> str:
    if exc.not_found:
        return "That title is no longer available in the API."
    if exc.rate_limited:
        return "The movie API is rate limited right now. Please try again in a moment."
    if exc.no_sources:
        return exc.message
    return exc.message


async def answer_rich_message(
    message: Message,
    text: str,
    *,
    reply_markup=None,
    poster_url: str = "",
) -> None:
    if poster_url:
        try:
            await message.answer_photo(photo=poster_url, caption=text, reply_markup=reply_markup)
            return
        except TelegramBadRequest:
            pass
    await message.answer(text, reply_markup=reply_markup)


async def edit_callback_message(
    query: CallbackQuery,
    text: str,
    *,
    reply_markup=None,
    poster_url: str = "",
) -> None:
    if not query.message:
        await query.answer(text, show_alert=True)
        return

    message = query.message
    if poster_url:
        if message.content_type == ContentType.PHOTO:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(media=poster_url, caption=text, parse_mode="HTML"),
                    reply_markup=reply_markup,
                )
                return
            except TelegramBadRequest:
                await _replace_with_text_message(message, text, reply_markup=reply_markup)
                return

        try:
            await message.answer_photo(photo=poster_url, caption=text, reply_markup=reply_markup)
            await _safe_delete(message)
            return
        except TelegramBadRequest:
            pass

    if message.content_type == ContentType.PHOTO:
        await _replace_with_text_message(message, text, reply_markup=reply_markup)
        return

    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def answer_callback_error(query: CallbackQuery, exc: ApiError) -> None:
    await edit_callback_message(query, format_error(readable_api_error(exc)))


async def _replace_with_text_message(message: Message, text: str, *, reply_markup=None) -> None:
    await message.answer(text, reply_markup=reply_markup)
    await _safe_delete(message)


async def _safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        return

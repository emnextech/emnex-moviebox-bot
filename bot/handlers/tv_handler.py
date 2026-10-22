from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.buttons import bulk_quality_keyboard, episode_keyboard, episode_quality_keyboard
from bot.utils.callbacks import (
    TvBulkSelectCallback,
    TvEpisodeCallback,
    TvEpisodePageCallback,
    TvSeasonCallback,
    UpgradePromptCallback,
)
from bot.utils.formatter import format_quality_prompt, format_tv_season_prompt

from .helpers import (
    answer_callback_error,
    edit_callback_message,
    page_bounds,
    readable_api_error,
    season_info_for,
    unique_variants,
)

router = Router(name="tv_handler")


def _is_private(query: CallbackQuery) -> bool:
    return bool(query.message and query.message.chat.type == "private")


@router.callback_query(F.data == "noop")
async def on_noop(query: CallbackQuery) -> None:
    await query.answer()


@router.callback_query(UpgradePromptCallback.filter())
async def on_upgrade_prompt(
    query: CallbackQuery,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer()
        return
    user = await services.user_service.ensure_user(query.from_user)
    await services.user_service.log_event(
        telegram_user_id=user.telegram_user_id,
        action="upgrade_prompt",
        outcome="shown",
        plan_at_time=user.active_plan,
    )
    await query.answer("Current-page TV episode links are a PRO feature. Use /pro to upgrade.", show_alert=True)


@router.callback_query(TvSeasonCallback.filter())
async def on_season_selected(
    query: CallbackQuery,
    callback_data: TvSeasonCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None:
            await query.answer("That season is not available.", show_alert=True)
            return

        start, end = page_bounds(services.settings, 0, season_info.max_episode)
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="select_season",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
        )
        await edit_callback_message(
            query,
            format_tv_season_prompt(media, callback_data.season, start, end),
            reply_markup=episode_keyboard(
                settings=services.settings,
                subject_id=media.subject_id,
                season=callback_data.season,
                page=0,
                max_episode=season_info.max_episode,
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(TvEpisodePageCallback.filter())
async def on_episode_page_changed(
    query: CallbackQuery,
    callback_data: TvEpisodePageCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None:
            await query.answer("That season is not available.", show_alert=True)
            return
        if callback_data.page < 0:
            await query.answer("That page is not available.", show_alert=True)
            return

        start, end = page_bounds(services.settings, callback_data.page, season_info.max_episode)
        if start > season_info.max_episode:
            await query.answer("That page is not available.", show_alert=True)
            return
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="episode_page",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
            metadata={"page": callback_data.page},
        )
        await edit_callback_message(
            query,
            format_tv_season_prompt(media, callback_data.season, start, end),
            reply_markup=episode_keyboard(
                settings=services.settings,
                subject_id=media.subject_id,
                season=callback_data.season,
                page=callback_data.page,
                max_episode=season_info.max_episode,
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(TvEpisodeCallback.filter())
async def on_episode_selected(
    query: CallbackQuery,
    callback_data: TvEpisodeCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None or callback_data.episode <= 0 or callback_data.episode > season_info.max_episode:
            await query.answer("That episode is not available.", show_alert=True)
            return
        sources = await services.api_client.get_sources(
            callback_data.subject_id,
            season=callback_data.season,
            episode=callback_data.episode,
        )
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="episode_sources",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
            episode=callback_data.episode,
        )
        await edit_callback_message(
            query,
            format_quality_prompt(
                media.title,
                user.active_plan,
                season=callback_data.season,
                episode=callback_data.episode,
            ),
            reply_markup=episode_quality_keyboard(
                settings=services.settings,
                plan=user.active_plan,
                subject_id=callback_data.subject_id,
                season=callback_data.season,
                episode=callback_data.episode,
                page=max(0, (callback_data.episode - 1) // services.settings.max_bulk_episodes),
                sources=unique_variants(sources),
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="episode_sources",
            outcome="error",
            plan_at_time=user.active_plan,
            subject_id=callback_data.subject_id,
            subject_type="tv",
            season=callback_data.season,
            episode=callback_data.episode,
            metadata={"message": readable_api_error(exc)},
        )
        await answer_callback_error(query, exc)


@router.callback_query(TvBulkSelectCallback.filter())
async def on_bulk_selected(
    query: CallbackQuery,
    callback_data: TvBulkSelectCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="bulk_select",
            outcome="upgrade_prompt",
            plan_at_time=user.active_plan,
            subject_id=callback_data.subject_id,
            subject_type="tv",
            season=callback_data.season,
            metadata={"page": callback_data.page},
        )
        await query.answer("Current-page TV episode links are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "source")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None:
            await query.answer("That season is not available.", show_alert=True)
            return
        if callback_data.page < 0:
            await query.answer("That page is not available.", show_alert=True)
            return
        start, end = page_bounds(services.settings, callback_data.page, season_info.max_episode)
        if start > season_info.max_episode:
            await query.answer("That page is not available.", show_alert=True)
            return
        sample_sources = await services.api_client.get_sources(
            callback_data.subject_id,
            season=callback_data.season,
            episode=start,
        )
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="bulk_select",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
            metadata={"page": callback_data.page, "start": start, "end": end},
        )
        await edit_callback_message(
            query,
            format_quality_prompt(
                media.title,
                user.active_plan,
                bulk_range=f"Episodes {start}-{end}",
            ),
            reply_markup=bulk_quality_keyboard(
                plan=user.active_plan,
                subject_id=callback_data.subject_id,
                season=callback_data.season,
                page=callback_data.page,
                sources=unique_variants(sample_sources),
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)

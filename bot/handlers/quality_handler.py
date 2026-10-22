from __future__ import annotations

import asyncio

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.buttons import bulk_direct_link_keyboard, source_action_keyboard, subtitle_keyboard
from bot.utils.callbacks import (
    MediaSelectCallback,
    MovieQualityCallback,
    SourceRefreshCallback,
    SubtitlePromptCallback,
    TvBulkQualityCallback,
    TvEpisodeCallback,
    TvEpisodeQualityCallback,
)
from bot.utils.formatter import format_bulk_links, format_source_actions, format_subtitles_prompt

from .helpers import (
    answer_callback_error,
    edit_callback_message,
    page_bounds,
    season_info_for,
    sources_for_variant,
)

router = Router(name="quality_handler")


def _is_private(query: CallbackQuery) -> bool:
    return bool(query.message and query.message.chat.type == "private")


@router.callback_query(MovieQualityCallback.filter())
async def on_movie_quality_selected(
    query: CallbackQuery,
    callback_data: MovieQualityCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await query.answer("Direct Telegram links are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "source")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        sources = await services.api_client.get_sources(callback_data.subject_id)
        matching = sources_for_variant(sources, callback_data.variant)
        if not matching:
            await query.answer("That quality variant is no longer available.", show_alert=True)
            return

        source = matching[0]
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="movie_direct_links",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="movie",
            quality=source.display_label,
        )
        await edit_callback_message(
            query,
            format_source_actions(media.title, source.display_label, user.active_plan),
            reply_markup=source_action_keyboard(
                source=source,
                refresh_callback=SourceRefreshCallback(subject_id=media.subject_id, variant=callback_data.variant).pack(),
                subtitle_callback=SubtitlePromptCallback(subject_id=media.subject_id, variant=callback_data.variant).pack(),
                back_callback=MediaSelectCallback(subject_id=media.subject_id).pack(),
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(TvEpisodeQualityCallback.filter())
async def on_episode_quality_selected(
    query: CallbackQuery,
    callback_data: TvEpisodeQualityCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await query.answer("Direct Telegram links are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "source")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None or callback_data.episode <= 0 or callback_data.episode > season_info.max_episode:
            await query.answer("That episode is no longer available.", show_alert=True)
            return
        sources = await services.api_client.get_sources(
            callback_data.subject_id,
            season=callback_data.season,
            episode=callback_data.episode,
        )
        matching = sources_for_variant(sources, callback_data.variant)
        if not matching:
            await query.answer("That quality variant is no longer available.", show_alert=True)
            return

        source = matching[0]
        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="episode_direct_link",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
            episode=callback_data.episode,
            quality=source.display_label,
        )
        await edit_callback_message(
            query,
            format_source_actions(
                media.title,
                source.display_label,
                user.active_plan,
                season=callback_data.season,
                episode=callback_data.episode,
            ),
            reply_markup=source_action_keyboard(
                source=source,
                refresh_callback=SourceRefreshCallback(
                    subject_id=callback_data.subject_id,
                    variant=callback_data.variant,
                    season=callback_data.season,
                    episode=callback_data.episode,
                ).pack(),
                subtitle_callback=SubtitlePromptCallback(
                    subject_id=callback_data.subject_id,
                    variant=callback_data.variant,
                    season=callback_data.season,
                    episode=callback_data.episode,
                ).pack(),
                back_callback=TvEpisodeCallback(
                    subject_id=callback_data.subject_id,
                    season=callback_data.season,
                    episode=callback_data.episode,
                ).pack(),
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(SourceRefreshCallback.filter())
async def on_source_refresh_selected(
    query: CallbackQuery,
    callback_data: SourceRefreshCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await query.answer("Direct Telegram links are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "source")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        sources = await services.api_client.get_sources(
            callback_data.subject_id,
            season=callback_data.season or None,
            episode=callback_data.episode or None,
            refresh=True,
        )
        matching = sources_for_variant(sources, callback_data.variant)
        if not matching:
            await query.answer("That quality variant is no longer available after refresh.", show_alert=True)
            return

        source = matching[0]
        back_callback = (
            MediaSelectCallback(subject_id=callback_data.subject_id).pack()
            if not callback_data.season or not callback_data.episode
            else TvEpisodeCallback(
                subject_id=callback_data.subject_id,
                season=callback_data.season,
                episode=callback_data.episode,
            ).pack()
        )
        await edit_callback_message(
            query,
            format_source_actions(
                media.title,
                source.display_label,
                user.active_plan,
                season=callback_data.season or None,
                episode=callback_data.episode or None,
            ),
            reply_markup=source_action_keyboard(
                source=source,
                refresh_callback=callback_data.pack(),
                subtitle_callback=SubtitlePromptCallback(
                    subject_id=callback_data.subject_id,
                    variant=callback_data.variant,
                    season=callback_data.season,
                    episode=callback_data.episode,
                ).pack(),
                back_callback=back_callback,
            ),
            poster_url=media.poster,
        )
        await query.answer("Links refreshed.")
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(SubtitlePromptCallback.filter())
async def on_subtitles_requested(
    query: CallbackQuery,
    callback_data: SubtitlePromptCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await query.answer("Subtitles inside Telegram are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        subtitles = await services.api_client.get_subtitles(
            callback_data.subject_id,
            season=callback_data.season or None,
            episode=callback_data.episode or None,
        )
        back_callback = (
            MovieQualityCallback(subject_id=callback_data.subject_id, variant=callback_data.variant).pack()
            if not callback_data.season or not callback_data.episode
            else TvEpisodeQualityCallback(
                subject_id=callback_data.subject_id,
                season=callback_data.season,
                episode=callback_data.episode,
                variant=callback_data.variant,
            ).pack()
        )
        await edit_callback_message(
            query,
            format_subtitles_prompt(
                media.title,
                subtitles,
                season=callback_data.season or None,
                episode=callback_data.episode or None,
            ),
            reply_markup=subtitle_keyboard(subtitles, back_callback=back_callback),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)


@router.callback_query(TvBulkQualityCallback.filter())
async def on_bulk_quality_selected(
    query: CallbackQuery,
    callback_data: TvBulkQualityCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private(query):
        await query.answer("Use this bot in a private chat.")
        return

    user = await services.user_service.ensure_user(query.from_user)
    if not user.is_pro:
        await query.answer("Current-page TV episode links are a PRO feature. Use /pro to upgrade.", show_alert=True)
        return

    allowed, retry_after = services.rate_limiter.check(user.telegram_user_id, "bulk")
    if not allowed:
        await query.answer(f"Try again in {retry_after}s.", show_alert=True)
        return

    try:
        media = await services.api_client.get_media_details(callback_data.subject_id)
        season_info = season_info_for(media, callback_data.season)
        if season_info is None:
            await query.answer("That season is no longer available.", show_alert=True)
            return
        if callback_data.page < 0:
            await query.answer("That page is no longer available.", show_alert=True)
            return

        start, end = page_bounds(services.settings, callback_data.page, season_info.max_episode)
        if start > season_info.max_episode:
            await query.answer("That page is no longer available.", show_alert=True)
            return
        sample_sources = await services.api_client.get_sources(
            callback_data.subject_id,
            season=callback_data.season,
            episode=start,
        )
        sample = sources_for_variant(sample_sources, callback_data.variant)
        variant_label = sample[0].display_label if sample else "Selected variant"
        semaphore = asyncio.Semaphore(services.settings.source_concurrency)

        async def resolve_episode(episode: int) -> tuple[int, str | None]:
            async with semaphore:
                try:
                    episode_sources = await services.api_client.get_sources(
                        callback_data.subject_id,
                        season=callback_data.season,
                        episode=episode,
                    )
                except ApiError:
                    return episode, None
                matches = sources_for_variant(episode_sources, callback_data.variant)
                return episode, matches[0].download_url if matches else None

        resolved = await asyncio.gather(*(resolve_episode(episode) for episode in range(start, end + 1)))
        ready_links = [(episode, url) for episode, url in resolved if url]
        missing = [episode for episode, url in resolved if not url]
        if not ready_links:
            await query.answer("No matching episode links were available for that quality.", show_alert=True)
            return

        await services.user_service.log_event(
            telegram_user_id=user.telegram_user_id,
            action="bulk_direct_links",
            outcome="success",
            plan_at_time=user.active_plan,
            subject_id=media.subject_id,
            subject_type="tv",
            season=callback_data.season,
            quality=variant_label,
            metadata={"page": callback_data.page, "delivered": len(ready_links), "missing": missing},
        )
        await edit_callback_message(
            query,
            format_bulk_links(
                media.title,
                callback_data.season,
                variant_label,
                len(ready_links),
                missing,
            ),
            reply_markup=bulk_direct_link_keyboard(
                subject_id=callback_data.subject_id,
                season=callback_data.season,
                page=callback_data.page,
                links=ready_links,
            ),
            poster_url=media.poster,
        )
        await query.answer()
    except ApiError as exc:
        await answer_callback_error(query, exc)

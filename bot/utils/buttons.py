from __future__ import annotations

from math import ceil
from typing import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.settings import Settings
from bot.models import DiscoverySection, MediaDetails, SearchResult, SourceOption, SubtitleOption, UserPlan
from bot.utils.catalog import FilterOption
from bot.utils.callbacks import (
    BrowseCatalogCallback,
    BrowseFilterOpenCallback,
    BrowsePresetCallback,
    BrowseFilterSetCallback,
    BrowseResetCallback,
    DiscoveryPageCallback,
    HomeSectionCallback,
    MediaSelectCallback,
    MovieQualityCallback,
    TvBulkQualityCallback,
    TvBulkSelectCallback,
    TvEpisodeCallback,
    TvEpisodePageCallback,
    TvEpisodeQualityCallback,
    TvSeasonCallback,
    UpgradePromptCallback,
)


def _truncate_title(title: str, *, limit: int = 28) -> str:
    return f"{title[:limit]}..." if len(title) > limit else title


def support_contact_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 WhatsApp", url=settings.pro_whatsapp_url),
                InlineKeyboardButton(text="📩 Telegram", url=settings.pro_telegram_url),
            ]
        ]
    )


def search_results_keyboard(
    results: list[SearchResult],
    *,
    callback_for: Callable[[SearchResult], str],
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=_truncate_title(item.title), callback_data=callback_for(item))] for item in results]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def home_sections_keyboard(sections: list[DiscoverySection], *, token: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=_truncate_title(f"{section.title} ({len(section.items)})", limit=32),
                callback_data=HomeSectionCallback(token=token, index=index).pack(),
            )
        ]
        for index, section in enumerate(sections)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def discovery_results_keyboard(
    items: list[SearchResult],
    *,
    callback_for: Callable[[SearchResult], str],
    prev_callback: str | None = None,
    next_callback: str | None = None,
    extra_rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=_truncate_title(item.title), callback_data=callback_for(item))] for item in items]
    nav_row: list[InlineKeyboardButton] = []
    if prev_callback:
        nav_row.append(InlineKeyboardButton(text="< Prev", callback_data=prev_callback))
    if next_callback:
        nav_row.append(InlineKeyboardButton(text="Next >", callback_data=next_callback))
    if nav_row:
        rows.append(nav_row)
    if extra_rows:
        rows.extend(extra_rows)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def browse_catalog_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Movies", callback_data=BrowseCatalogCallback(channel_id=1).pack()),
                InlineKeyboardButton(text="📺 TV Shows", callback_data=BrowseCatalogCallback(channel_id=2).pack()),
            ],
            [
                InlineKeyboardButton(text="🎞 Animations", callback_data=BrowsePresetCallback(preset="animation").pack()),
            ],
        ]
    )


def browse_results_controls_keyboard(token: str, *, page: int, prev_page: bool, next_page: bool) -> list[list[InlineKeyboardButton]]:
    rows = [
        [
            InlineKeyboardButton(text="🎭 Genre", callback_data=BrowseFilterOpenCallback(token=token, field="g", page=0).pack()),
            InlineKeyboardButton(text="🌍 Country", callback_data=BrowseFilterOpenCallback(token=token, field="c", page=0).pack()),
        ],
        [
            InlineKeyboardButton(text="📅 Year", callback_data=BrowseFilterOpenCallback(token=token, field="y", page=0).pack()),
            InlineKeyboardButton(text="🗣 Language", callback_data=BrowseFilterOpenCallback(token=token, field="l", page=0).pack()),
        ],
        [
            InlineKeyboardButton(text="↕️ Sort", callback_data=BrowseFilterOpenCallback(token=token, field="s", page=0).pack()),
            InlineKeyboardButton(text="🔄 Reset", callback_data=BrowseResetCallback(token=token).pack()),
        ],
    ]
    nav_row: list[InlineKeyboardButton] = []
    if prev_page:
        nav_row.append(InlineKeyboardButton(text="< Prev", callback_data=DiscoveryPageCallback(token=token, page=page - 1).pack()))
    nav_row.append(InlineKeyboardButton(text=f"{page}", callback_data="noop"))
    if next_page:
        nav_row.append(InlineKeyboardButton(text="Next >", callback_data=DiscoveryPageCallback(token=token, page=page + 1).pack()))
    rows.append(nav_row)
    return rows


def browse_filter_keyboard(
    *,
    token: str,
    field: str,
    options: tuple[FilterOption, ...],
    selected_value: str,
    page: int,
    back_callback: str,
) -> InlineKeyboardMarkup:
    per_page = 8
    start = page * per_page
    end = min(len(options), start + per_page)

    rows = []
    for index in range(start, end):
        option = options[index]
        text = f"• {option.label}" if option.value == selected_value else option.label
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=BrowseFilterSetCallback(token=token, field=field, index=index).pack(),
                )
            ]
        )

    total_pages = max(1, ceil(len(options) / per_page))
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="< Prev",
                callback_data=BrowseFilterOpenCallback(token=token, field=field, page=page - 1).pack(),
            )
        )
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Next >",
                callback_data=BrowseFilterOpenCallback(token=token, field=field, page=page + 1).pack(),
            )
        )
    rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="< Back to Results", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def movie_quality_keyboard(
    *,
    settings: Settings,
    plan: UserPlan,
    media: MediaDetails,
    sources: list[SourceOption],
    footer_rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources:
        if plan == UserPlan.PRO:
            button = InlineKeyboardButton(
                text=source.display_label,
                callback_data=MovieQualityCallback(subject_id=media.subject_id, variant=source.variant_id).pack(),
            )
        else:
            url = f"{settings.site_base_url}/movie/{media.subject_id}?ref=telegram&tier=basic&quality={source.quality}#download-section"
            button = InlineKeyboardButton(text=source.display_label, url=url)
        rows.append([button])
    if footer_rows:
        rows.extend(footer_rows)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def season_keyboard(
    media: MediaDetails,
    *,
    footer_rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for season in media.seasons:
        current_row.append(
            InlineKeyboardButton(
                text=f"Season {season.season_number}",
                callback_data=TvSeasonCallback(subject_id=media.subject_id, season=season.season_number).pack(),
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    if footer_rows:
        rows.extend(footer_rows)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def episode_keyboard(
    *,
    settings: Settings,
    subject_id: str,
    season: int,
    page: int,
    max_episode: int,
) -> InlineKeyboardMarkup:
    per_page = settings.max_bulk_episodes
    start = page * per_page + 1
    end = min(max_episode, start + per_page - 1)

    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for episode in range(start, end + 1):
        current_row.append(
            InlineKeyboardButton(
                text=f"Ep {episode}",
                callback_data=TvEpisodeCallback(subject_id=subject_id, season=season, episode=episode).pack(),
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append(
        [
            InlineKeyboardButton(
                text="📦 Episode Links for This Page",
                callback_data=TvBulkSelectCallback(subject_id=subject_id, season=season, page=page).pack(),
            )
        ]
    )

    total_pages = max(1, ceil(max_episode / per_page))
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="< Prev",
                callback_data=TvEpisodePageCallback(subject_id=subject_id, season=season, page=page - 1).pack(),
            )
        )
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Next >",
                callback_data=TvEpisodePageCallback(subject_id=subject_id, season=season, page=page + 1).pack(),
            )
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def episode_quality_keyboard(
    *,
    settings: Settings,
    plan: UserPlan,
    subject_id: str,
    season: int,
    episode: int,
    page: int,
    sources: list[SourceOption],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for source in sources:
        if plan == UserPlan.PRO:
            button = InlineKeyboardButton(
                text=source.display_label,
                callback_data=TvEpisodeQualityCallback(
                    subject_id=subject_id,
                    season=season,
                    episode=episode,
                    variant=source.variant_id,
                ).pack(),
            )
        else:
            url = (
                f"{settings.site_base_url}/watch/{subject_id}"
                f"?season={season}&episode={episode}&ref=telegram&tier=basic"
            )
            button = InlineKeyboardButton(text=source.display_label, url=url)
        rows.append([button])
    rows.append(
        [
            InlineKeyboardButton(
                text="< Back to Episodes",
                callback_data=TvEpisodePageCallback(subject_id=subject_id, season=season, page=page).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bulk_quality_keyboard(
    *,
    plan: UserPlan,
    subject_id: str,
    season: int,
    page: int,
    sources: list[SourceOption],
) -> InlineKeyboardMarkup:
    if plan != UserPlan.PRO:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✨ Unlock PRO",
                        callback_data=UpgradePromptCallback(subject_id=subject_id, season=season, page=page).pack(),
                    )
                ]
            ]
        )

    rows = [
        [
            InlineKeyboardButton(
                text=source.display_label,
                callback_data=TvBulkQualityCallback(
                    subject_id=subject_id,
                    season=season,
                    page=page,
                    variant=source.variant_id,
                ).pack(),
            )
        ]
        for source in sources
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def source_action_keyboard(
    *,
    source: SourceOption,
    refresh_callback: str,
    subtitle_callback: str,
    back_callback: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="⬇️ Download", url=source.download_url)],
    ]
    if source.stream_url:
        rows.append([InlineKeyboardButton(text="▶️ Stream", url=source.stream_url)])
    rows.append([InlineKeyboardButton(text="💬 Subtitles", callback_data=subtitle_callback)])
    rows.append([InlineKeyboardButton(text="🔄 Refresh Links", callback_data=refresh_callback)])
    rows.append([InlineKeyboardButton(text="< Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subtitle_keyboard(subtitles: list[SubtitleOption], *, back_callback: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"💬 {subtitle.display_label}", url=subtitle.url)]
        for subtitle in subtitles
    ]
    rows.append([InlineKeyboardButton(text="< Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bulk_direct_link_keyboard(
    *,
    subject_id: str,
    season: int,
    page: int,
    links: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"Episode {episode}", url=url)] for episode, url in links]
    rows.append(
        [
            InlineKeyboardButton(
                text="< Back",
                callback_data=TvEpisodePageCallback(subject_id=subject_id, season=season, page=page).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

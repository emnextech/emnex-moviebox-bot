from __future__ import annotations

from math import ceil
from typing import Any

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from bot.models import BrowseState, PagedResult, SearchResult
from bot.runtime import ServiceContainer
from bot.services import ApiError
from bot.utils.buttons import (
    browse_catalog_keyboard,
    browse_filter_keyboard,
    browse_results_controls_keyboard,
    discovery_results_keyboard,
    home_sections_keyboard,
)
from bot.utils.callbacks import (
    BrowseCatalogCallback,
    BrowseFilterOpenCallback,
    BrowsePresetCallback,
    BrowseFilterSetCallback,
    BrowseResetCallback,
    DiscoveryPageCallback,
    HomeSectionCallback,
    MediaSelectCallback,
)
from bot.utils.catalog import options_for
from bot.utils.formatter import (
    format_browse_filter_prompt,
    format_browse_summary,
    format_discovery_page,
    format_error,
    format_home_sections,
)

from .helpers import answer_callback_error, answer_rich_message, edit_callback_message

router = Router(name="discovery_handler")


def _is_private_query(query: CallbackQuery) -> bool:
    return bool(query.message and query.message.chat.type == "private")


def _state_for(token: str, *, user_id: int, services: ServiceContainer) -> dict[str, Any] | None:
    payload = services.session_store.get(token)
    if not isinstance(payload, dict):
        return None
    if payload.get("owner_id") != user_id:
        return None
    return payload


def _media_callback_data(
    item: SearchResult,
    *,
    services: ServiceContainer,
    owner_id: int,
    origin: str,
) -> str:
    ref = services.session_store.put({"owner_id": owner_id, "poster": item.poster, "origin": origin})
    return MediaSelectCallback(subject_id=item.subject_id, ref=ref).pack()


async def send_home_sections(message: Message, user_id: int, services: ServiceContainer) -> None:
    sections = await services.api_client.get_homepage_sections()
    if not sections:
        await answer_rich_message(message, format_error("Home sections are not available right now."))
        return
    token = services.session_store.put({"owner_id": user_id, "kind": "home", "sections": sections})
    poster = next((item.poster for section in sections for item in section.items if item.poster), "")
    await answer_rich_message(
        message,
        format_home_sections(sections),
        reply_markup=home_sections_keyboard(sections, token=token),
        poster_url=poster,
    )


async def send_browse_chooser(message: Message) -> None:
    await answer_rich_message(
        message,
        "<b>🧭 Browse Catalog</b>\n\nChoose the catalog you want to explore.",
        reply_markup=browse_catalog_keyboard(),
    )


@router.callback_query(HomeSectionCallback.filter())
async def on_home_section_selected(
    query: CallbackQuery,
    callback_data: HomeSectionCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    state = _state_for(callback_data.token, user_id=query.from_user.id, services=services)
    if state is None or state.get("kind") != "home":
        await query.answer("That discover menu expired. Open /discover again.", show_alert=True)
        return

    sections = state.get("sections") or []
    if callback_data.index < 0 or callback_data.index >= len(sections):
        await query.answer("That section is not available.", show_alert=True)
        return

    section = sections[callback_data.index]
    next_token = services.session_store.put(
        {
            "owner_id": query.from_user.id,
            "kind": "static",
            "title": section.title,
            "items": list(section.items),
            "page": 1,
        }
    )
    await _render_state_query(query, services=services, state_token=next_token)
    await query.answer()


@router.callback_query(DiscoveryPageCallback.filter())
async def on_discovery_page_changed(
    query: CallbackQuery,
    callback_data: DiscoveryPageCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    state = _state_for(callback_data.token, user_id=query.from_user.id, services=services)
    if state is None:
        await query.answer("That menu expired. Open it again.", show_alert=True)
        return

    next_page = max(1, callback_data.page)
    if state.get("kind") == "browse":
        browse_state = state.get("browse")
        if not isinstance(browse_state, BrowseState):
            await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
            return
        browse_state.page = next_page
        state["browse"] = browse_state
    else:
        state["page"] = next_page
    services.session_store.replace(callback_data.token, state)
    await _render_state_query(query, services=services, state_token=callback_data.token)
    await query.answer()


@router.callback_query(BrowseCatalogCallback.filter())
async def on_browse_catalog_selected(
    query: CallbackQuery,
    callback_data: BrowseCatalogCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    token = services.session_store.put(
        {
            "owner_id": query.from_user.id,
            "kind": "browse",
            "title": "🧭 Browse Results",
            "browse": BrowseState(channel_id=callback_data.channel_id),
        }
    )
    await _render_state_query(query, services=services, state_token=token)
    await query.answer()


@router.callback_query(BrowsePresetCallback.filter())
async def on_browse_preset_selected(
    query: CallbackQuery,
    callback_data: BrowsePresetCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    if callback_data.preset != "animation":
        await query.answer("That preset is not available.", show_alert=True)
        return

    token = services.session_store.put(
        {
            "owner_id": query.from_user.id,
            "kind": "browse",
            "title": "🎞 Animation Movies",
            "browse": BrowseState(channel_id=1, genre="Animation"),
        }
    )
    await _render_state_query(query, services=services, state_token=token)
    await query.answer()


@router.callback_query(BrowseFilterOpenCallback.filter())
async def on_browse_filter_opened(
    query: CallbackQuery,
    callback_data: BrowseFilterOpenCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    state = _state_for(callback_data.token, user_id=query.from_user.id, services=services)
    if state is None or state.get("kind") != "browse":
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    browse_state = state.get("browse")
    if not isinstance(browse_state, BrowseState):
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    options = options_for(callback_data.field)
    if not options:
        await query.answer("That filter is not available.", show_alert=True)
        return

    total_pages = max(1, ceil(len(options) / 8))
    page = min(max(callback_data.page, 0), total_pages - 1)
    selected_value = _browse_value_for_field(browse_state, callback_data.field)
    await edit_callback_message(
        query,
        format_browse_filter_prompt(browse_state, callback_data.field, page=page, total_pages=total_pages),
        reply_markup=browse_filter_keyboard(
            token=callback_data.token,
            field=callback_data.field,
            options=options,
            selected_value=selected_value,
            page=page,
            back_callback=DiscoveryPageCallback(token=callback_data.token, page=browse_state.page).pack(),
        ),
    )
    await query.answer()


@router.callback_query(BrowseFilterSetCallback.filter())
async def on_browse_filter_selected(
    query: CallbackQuery,
    callback_data: BrowseFilterSetCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    state = _state_for(callback_data.token, user_id=query.from_user.id, services=services)
    if state is None or state.get("kind") != "browse":
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    browse_state = state.get("browse")
    if not isinstance(browse_state, BrowseState):
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    options = options_for(callback_data.field)
    if callback_data.index < 0 or callback_data.index >= len(options):
        await query.answer("That option is not available.", show_alert=True)
        return

    option = options[callback_data.index]
    _set_browse_value_for_field(browse_state, callback_data.field, option.value)
    browse_state.page = 1
    state["browse"] = browse_state
    services.session_store.replace(callback_data.token, state)
    await _render_state_query(query, services=services, state_token=callback_data.token)
    await query.answer()


@router.callback_query(BrowseResetCallback.filter())
async def on_browse_reset(
    query: CallbackQuery,
    callback_data: BrowseResetCallback,
    services: ServiceContainer,
) -> None:
    if not _is_private_query(query):
        await query.answer()
        return

    state = _state_for(callback_data.token, user_id=query.from_user.id, services=services)
    if state is None or state.get("kind") != "browse":
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    browse_state = state.get("browse")
    if not isinstance(browse_state, BrowseState):
        await query.answer("That browse menu expired. Open /browse again.", show_alert=True)
        return

    state["browse"] = BrowseState(channel_id=browse_state.channel_id)
    services.session_store.replace(callback_data.token, state)
    await _render_state_query(query, services=services, state_token=callback_data.token)
    await query.answer()


async def _render_state_message(message: Message, *, services: ServiceContainer, state_token: str) -> None:
    state = services.session_store.get(state_token)
    if not isinstance(state, dict):
        await answer_rich_message(message, format_error("That menu expired. Please open it again."))
        return
    try:
        text, poster_url, keyboard = await _build_state_view(state, state_token=state_token, services=services)
    except ApiError as exc:
        await answer_rich_message(message, format_error(exc.message))
        return
    await answer_rich_message(message, text, reply_markup=keyboard, poster_url=poster_url)


async def _render_state_query(query: CallbackQuery, *, services: ServiceContainer, state_token: str) -> None:
    state = services.session_store.get(state_token)
    if not isinstance(state, dict):
        await query.answer("That menu expired. Please open it again.", show_alert=True)
        return
    try:
        text, poster_url, keyboard = await _build_state_view(state, state_token=state_token, services=services)
    except ApiError as exc:
        await answer_callback_error(query, exc)
        return
    await edit_callback_message(query, text, reply_markup=keyboard, poster_url=poster_url)


async def _build_state_view(
    state: dict[str, Any],
    *,
    state_token: str,
    services: ServiceContainer,
) -> tuple[str, str, Any]:
    kind = state.get("kind")
    if kind == "static":
        all_items = list(state.get("items") or [])
        page = max(1, int(state.get("page") or 1))
        per_page = services.settings.max_search_results
        start = (page - 1) * per_page
        end = start + per_page
        result = PagedResult(
            items=all_items[start:end],
            page=page,
            has_more=end < len(all_items),
            total=len(all_items),
        )
        summary = None
    elif kind == "browse":
        browse_state = state.get("browse")
        if not isinstance(browse_state, BrowseState):
            raise ApiError("That browse menu expired. Open /browse again.")
        result = await services.api_client.browse(browse_state, per_page=services.settings.max_search_results)
        summary = format_browse_summary(browse_state)
    else:
        raise ApiError("That menu is no longer available.")

    title = str(state.get("title") or "Titles")
    callback_for = lambda item: _media_callback_data(
        item,
        services=services,
        owner_id=int(state.get("owner_id") or 0),
        origin=str(kind),
    )
    poster_url = next((item.poster for item in result.items if item.poster), "")

    if kind == "browse":
        browse_state = state.get("browse")
        keyboard = discovery_results_keyboard(
            result.items,
            callback_for=callback_for,
            extra_rows=browse_results_controls_keyboard(
                state_token,
                page=browse_state.page,
                prev_page=browse_state.page > 1,
                next_page=result.has_more,
            ),
        )
    else:
        keyboard = discovery_results_keyboard(
            result.items,
            callback_for=callback_for,
            prev_callback=DiscoveryPageCallback(token=state_token, page=result.page - 1).pack() if result.page > 1 else None,
            next_callback=DiscoveryPageCallback(token=state_token, page=result.page + 1).pack() if result.has_more else None,
        )

    return (
        format_discovery_page(title, result.items, page=result.page, has_more=result.has_more, summary=summary),
        poster_url,
        keyboard,
    )


def _browse_value_for_field(state: BrowseState, field: str) -> str:
    if field == "g":
        return state.genre
    if field == "c":
        return state.country
    if field == "y":
        return state.year
    if field == "l":
        return state.classify
    if field == "s":
        return state.sort or "Hottest"
    return ""


def _set_browse_value_for_field(state: BrowseState, field: str, value: str) -> None:
    if field == "g":
        state.genre = value
    elif field == "c":
        state.country = value
    elif field == "y":
        state.year = value
    elif field == "l":
        state.classify = value
    elif field == "s":
        state.sort = value

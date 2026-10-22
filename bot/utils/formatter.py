from __future__ import annotations

from datetime import timezone
from html import escape

from bot.config.settings import Settings
from bot.models import BrowseState, DiscoverySection, MediaDetails, SearchResult, SubtitleOption, TelegramUserRecord, UserPlan
from bot.services.user_service import BotStats
from bot.utils.catalog import label_for


def compact_description(text: str, *, limit: int = 260) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def plan_label(plan: UserPlan) -> str:
    return "✨ PRO" if plan == UserPlan.PRO else "🆓 BASIC"


def format_welcome(settings: Settings) -> str:
    return (
        f"<b>🎬 {escape(settings.bot_name)}</b>\n\n"
        "Send any movie or TV title in this private chat and I'll find it for you.\n\n"
        "<b>🆓 BASIC</b>\n"
        "- Search movies and TV shows\n"
        "- See posters, quality options, and title details\n"
        "- Open the website for downloads\n\n"
        f"<b>✨ PRO • {escape(settings.pro_price_label)}</b>\n"
        "- Direct Telegram download links for movies\n"
        "- Direct Telegram download links for single episodes\n"
        "- Episode links for the current TV page\n"
        "- 1080p, audio variants, subtitles, and stream actions when available\n\n"
        "Try /discover for curated sections, /browse for movies, TV shows, and animations, or /help to see all commands."
    )


def format_help(settings: Settings) -> str:
    return (
        "<b>🧭 How to Use This Bot</b>\n\n"
        "1. Send a movie or TV show title.\n"
        "2. Tap a result.\n"
        "3. Choose a quality, season, or episode.\n\n"
        "<b>Commands</b>\n"
        "- /start - Welcome screen\n"
        "- /help - This help screen\n"
        "- /plan - Your current plan and User ID\n"
        "- /pro - PRO benefits and upgrade contacts\n"
        "- /search &lt;title&gt; - Search directly\n"
        "- /discover - Curated sections\n"
        "- /browse - Filter movies, TV shows, or animations\n\n"
        f"Private chat only. Support fallback: {escape(settings.support_contact)}"
    )


def format_plan(user: TelegramUserRecord, settings: Settings) -> str:
    expiry = "Not active"
    if user.plan_expires_at and user.active_plan == UserPlan.PRO:
        expiry = user.plan_expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        "<b>💳 Your Plan</b>\n\n"
        f"Tier: <b>{plan_label(user.active_plan)}</b>\n"
        f"🆓 BASIC: <b>Free</b>\n"
        f"✨ PRO: <b>{escape(settings.pro_price_label)}</b>\n"
        f"User ID: <code>{user.telegram_user_id}</code>\n"
        f"Expiry: {escape(expiry)}\n\n"
        "BASIC opens the website for downloads.\n"
        "PRO unlocks direct Telegram links, stream actions, subtitles, and current-page TV episode links.\n\n"
        "To upgrade:\n"
        "1. Open /pro.\n"
        "2. Share this User ID when you contact support.\n"
        "3. After payment is confirmed, PRO is activated."
    )


def format_pro_pitch(settings: Settings) -> str:
    return (
        "<b>✨ PRO Membership</b>\n\n"
        f"Price: <b>{escape(settings.pro_price_label)}</b>\n\n"
        "- Direct Telegram download links for movies\n"
        "- Direct Telegram download links for single episodes\n"
        "- Episode links for the current TV page\n"
        "- 1080p and audio variants when available\n"
        "- Refresh stale links\n"
        "- Subtitle buttons when available\n"
        "- Stream buttons when available\n\n"
        "Upgrade steps:\n"
        "1. Tap a contact button below.\n"
        "2. Send your User ID from /plan.\n"
        "3. After payment is confirmed, PRO is activated."
    )


def format_search_results(query: str, results: list[SearchResult], total: int) -> str:
    lines = [f"<b>🔎 Search Results</b> for <b>{escape(query)}</b>"]
    if total > len(results):
        lines.append(f"Showing <b>{len(results)}</b> of <b>{total}</b> matches.")
    lines.append("")
    for index, item in enumerate(results, start=1):
        year = f" ({escape(item.year)})" if item.year else ""
        lines.append(f"{index}. {escape(item.title)}{year} - {escape(item.media_label)}")
    lines.append("")
    lines.append("Tap a title below.")
    return "\n".join(lines)


def format_media_details(media: MediaDetails, plan: UserPlan) -> str:
    description = compact_description(media.description or "No description available yet.")
    facts: list[str] = []
    if media.year:
        facts.append(media.year)
    if media.rating:
        facts.append(f"Rating {media.rating}")
    if media.country_name:
        facts.append(media.country_name)
    if media.duration:
        facts.append(f"{media.duration} min")
    if media.genres:
        facts.append(", ".join(media.genres[:3]))
    if media.cast:
        facts.append(f"Cast: {', '.join(media.cast[:3])}")

    lines = [
        f"<b>{escape(media.title)}</b>",
        f"Type: <b>{escape(media.media_label)}</b>",
    ]
    if facts:
        lines.append(escape(" | ".join(facts)))
    lines.extend(
        [
            "",
            escape(description),
            "",
            f"Tier: <b>{plan_label(plan)}</b>",
            "Choose a quality below." if media.is_movie else "Choose a season below.",
        ]
    )
    return "\n".join(lines)


def format_tv_season_prompt(media: MediaDetails, season: int, start_episode: int, end_episode: int) -> str:
    return (
        f"<b>{escape(media.title)}</b>\n"
        f"Season <b>{season}</b>\n"
        f"Episodes <b>{start_episode}</b>-<b>{end_episode}</b>\n\n"
        "Choose one episode or get episode links for this page."
    )


def format_quality_prompt(
    title: str,
    plan: UserPlan,
    *,
    season: int | None = None,
    episode: int | None = None,
    bulk_range: str | None = None,
) -> str:
    lines = [f"<b>{escape(title)}</b>"]
    if season is not None and episode is not None:
        lines.append(f"Season <b>{season}</b> | Episode <b>{episode}</b>")
    if bulk_range:
        lines.append(f"Range: <b>{escape(bulk_range)}</b>")
    lines.append("")
    if plan == UserPlan.BASIC:
        lines.append("Tap a quality option.")
    elif bulk_range:
        lines.append("Tap a quality option and I'll gather one episode link per button for this page.")
    else:
        lines.append("Tap a quality option to open direct Telegram actions.")
    return "\n".join(lines)


def format_source_actions(
    title: str,
    variant_label: str,
    plan: UserPlan,
    *,
    season: int | None = None,
    episode: int | None = None,
) -> str:
    lines = [
        f"<b>{escape(title)}</b>",
        f"Variant: <b>{escape(variant_label)}</b>",
    ]
    if season is not None and episode is not None:
        lines.append(f"Season <b>{season}</b> | Episode <b>{episode}</b>")
    lines.extend(
        [
            f"Tier: <b>{plan_label(plan)}</b>",
            "",
            "Choose an action below.",
        ]
    )
    return "\n".join(lines)


def format_subtitles_prompt(
    title: str,
    subtitles: list[SubtitleOption],
    *,
    season: int | None = None,
    episode: int | None = None,
) -> str:
    lines = [f"<b>💬 Subtitles for {escape(title)}</b>"]
    if season is not None and episode is not None:
        lines.append(f"Season <b>{season}</b> | Episode <b>{episode}</b>")
    lines.append("")
    if subtitles:
        lines.append(f"Available subtitle tracks: <b>{len(subtitles)}</b>")
        for subtitle in subtitles[:8]:
            lines.append(f"- {escape(subtitle.display_label)}")
        lines.append("")
        lines.append("Tap a subtitle below.")
    else:
        lines.append("No subtitle tracks are available for this selection right now.")
    return "\n".join(lines)


def format_bulk_links(
    title: str,
    season: int,
    variant_label: str,
    delivered: int,
    missing: list[int],
) -> str:
    lines = [
        f"<b>{escape(title)}</b>",
        f"Season <b>{season}</b> | Variant: <b>{escape(variant_label)}</b>",
        "",
        f"Resolved episode links: <b>{delivered}</b>",
        "Telegram will show one button per episode below.",
    ]
    if missing:
        lines.append(f"Unavailable episodes: <b>{', '.join(str(item) for item in missing)}</b>")
    else:
        lines.append("All selected episodes were resolved successfully.")
    return "\n".join(lines)


def format_upgrade_prompt(settings: Settings) -> str:
    return (
        "<b>✨ Current-page TV episode links are a PRO feature.</b>\n\n"
        f"PRO is {escape(settings.pro_price_label)} and unlocks direct Telegram links for each episode on this page.\n"
        "Open /pro for the upgrade contacts."
    )


def format_home_sections(sections: list[DiscoverySection]) -> str:
    lines = ["<b>🔍 Discover</b>", "", "Tap a section below to open its titles."]
    for index, section in enumerate(sections, start=1):
        lines.append(f"{index}. {escape(section.title)}")
    return "\n".join(lines)


def format_discovery_page(
    title: str,
    items: list[SearchResult],
    *,
    page: int,
    has_more: bool,
    summary: str | None = None,
) -> str:
    lines = [f"<b>{escape(title)}</b>", f"Page <b>{page}</b>"]
    if summary:
        lines.extend(["", escape(summary)])
    lines.append("")
    if not items:
        lines.append("No titles are available right now.")
        return "\n".join(lines)
    for index, item in enumerate(items, start=1):
        year = f" ({escape(item.year)})" if item.year else ""
        lines.append(f"{index}. {escape(item.title)}{year} - {escape(item.media_label)}")
    lines.append("")
    lines.append("Tap a title below.")
    if has_more:
        lines.append("Use Next to load more.")
    return "\n".join(lines)


def format_browse_summary(state: BrowseState) -> str:
    sort_value = state.sort or "Hottest"
    return (
        f"Catalog: {state.catalog_label} | Genre: {state.genre} | Country: {state.country}\n"
        f"Year: {state.year} | Language: {state.classify} | Sort: {sort_value}"
    )


def format_browse_filter_prompt(state: BrowseState, filter_key: str, *, page: int, total_pages: int) -> str:
    values = {
        "g": state.genre,
        "c": state.country,
        "y": state.year,
        "l": state.classify,
        "s": state.sort or "Hottest",
    }
    return (
        f"<b>🧭 Browse {escape(state.catalog_label)}</b>\n"
        f"Choose <b>{escape(label_for(filter_key))}</b>\n"
        f"Current: <b>{escape(values.get(filter_key, ''))}</b>\n"
        f"Options page <b>{page + 1}/{total_pages}</b>"
    )


def format_error(message: str) -> str:
    return f"<b>Request failed</b>\n\n{escape(message)}"


def format_admin_user(user: TelegramUserRecord | None) -> str:
    if user is None:
        return "User not found."
    expiry = user.plan_expires_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if user.plan_expires_at else "None"
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip() or "-"
    return (
        "<b>User Lookup</b>\n\n"
        f"ID: <code>{user.telegram_user_id}</code>\n"
        f"Username: {escape(user.username or '-')}\n"
        f"Name: {escape(name)}\n"
        f"Tier: <b>{plan_label(user.active_plan)}</b>\n"
        f"Stored plan: <code>{user.plan.value}</code>\n"
        f"Expiry: {escape(expiry)}"
    )


def format_admin_stats(stats: BotStats) -> str:
    return (
        "<b>Bot Stats</b>\n\n"
        f"Total users: <b>{stats.total_users}</b>\n"
        f"Active PRO users: <b>{stats.active_pro_users}</b>\n"
        f"Events in last 24h: <b>{stats.events_last_24h}</b>"
    )

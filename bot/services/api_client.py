from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from bot.config.settings import Settings
from bot.models import (
    BrowseState,
    DiscoverySection,
    MediaDetails,
    PagedResult,
    SearchResult,
    SeasonInfo,
    SourceOption,
    SubtitleOption,
)


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        not_found: bool = False,
        rate_limited: bool = False,
        no_sources: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.not_found = not_found
        self.rate_limited = rate_limited
        self.no_sources = no_sources


def _human_size(size: Any) -> str:
    try:
        n = float(size)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.1f} {units[i]}"


class WorkerApiClient:
    """Talks to the cloud MovieBox worker (Supabase Edge Function, ?action= dialect).

    Streaming + downloads are delivered via the website (SITE_BASE_URL); the bot
    hands out links rather than files (Telegram can't ship multi-GB movies).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.worker_api_base,
            timeout=httpx.Timeout(settings.worker_timeout_seconds),
            headers={
                "Accept": "application/json",
                "User-Agent": "EmnexMoviesBot/2.0",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ---- website link builders -------------------------------------------
    def _watch_url(
        self,
        subject_id: str,
        *,
        season: int | None,
        episode: int | None,
        quality: str | None = None,
        download: bool = False,
    ) -> str:
        site = self.settings.site_base_url
        parts = [f"id={quote(str(subject_id))}"]
        if season is not None and episode is not None:
            parts.append(f"se={season}")
            parts.append(f"ep={episode}")
        if quality:
            parts.append(f"q={quote(quality)}")
        if download:
            parts.append("dl=1")
        page = "download" if download else "watch"
        return f"{site}/{page}?{'&'.join(parts)}"

    # ---- core API --------------------------------------------------------
    async def search(self, query: str) -> list[SearchResult]:
        payload = await self._get({"action": "search", "q": query.strip()})
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return []
        return [r for item in items if (r := self._parse_item(item))]

    async def get_media_details(self, subject_id: str) -> MediaDetails:
        d = await self._get({"action": "detail", "id": subject_id})
        if not isinstance(d, dict) or not d.get("id"):
            raise ApiError("Title not found.", not_found=True)
        subject_type = 2 if str(d.get("type")) == "tv" else 1
        seasons = [
            SeasonInfo(season_number=int(s.get("season") or 0), max_episode=int(s.get("episodes") or 0))
            for s in (d.get("seasons") or [])
            if int(s.get("season") or 0) > 0 and int(s.get("episodes") or 0) > 0
        ]
        return MediaDetails(
            subject_id=str(d.get("id")),
            title=str(d.get("title") or "Unknown Title"),
            subject_type=subject_type,
            year=str(d.get("year") or "")[:4],
            rating=str(d.get("rating") or ""),
            description=str(d.get("overview") or ""),
            poster=str(d.get("poster") or ""),
            genres=[g for g in (d.get("genres") or []) if g],
            seasons=sorted(seasons, key=lambda s: s.season_number),
            duration=str(d.get("duration") or ""),
        )

    async def get_sources(
        self,
        subject_id: str,
        *,
        season: int | None = None,
        episode: int | None = None,
        refresh: bool = False,
    ) -> list[SourceOption]:
        params: dict[str, Any] = {"action": "download", "id": subject_id}
        if season is not None and episode is not None:
            params["se"] = season
            params["ep"] = episode
        data = await self._get(params)
        if not isinstance(data, dict):
            raise ApiError("No sources available right now.", no_sources=True)
        resolutions = [r.strip() for r in str(data.get("resolutions") or "").split(",") if r.strip()]
        if not resolutions:
            raise ApiError("No sources are available for this title yet.", no_sources=True)
        size = _human_size(data.get("size"))
        ordered = sorted(resolutions, key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
        sources: list[SourceOption] = []
        for res in ordered:
            q = f"{res}p"
            sources.append(
                SourceOption(
                    quality=q,
                    download_url=self._watch_url(subject_id, season=season, episode=episode, quality=res, download=True),
                    size=size,
                    direct_url=self._watch_url(subject_id, season=season, episode=episode, quality=res, download=True),
                    stream_url=self._watch_url(subject_id, season=season, episode=episode, quality=res),
                    quality_num=int(res) if res.isdigit() else 0,
                    is_recommended=(res == ordered[0]),
                )
            )
        return sources

    async def get_subtitles(
        self,
        subject_id: str,
        *,
        season: int | None = None,
        episode: int | None = None,
    ) -> list[SubtitleOption]:
        # Worker doesn't expose subtitles yet; the website player loads them.
        return []

    # ---- discovery (not yet in the cloud worker -> empty, graceful) ------
    async def get_homepage_sections(self) -> list[DiscoverySection]:
        return []

    async def get_trending(self, *, page: int, per_page: int) -> PagedResult:
        return PagedResult(items=[], page=page, has_more=False)

    async def get_anime_dubbed(self, *, page: int, per_page: int) -> PagedResult:
        return PagedResult(items=[], page=page, has_more=False)

    async def get_similar_anime(self, *, subject_id: str, per_page: int) -> PagedResult:
        return PagedResult(items=[], page=1, has_more=False)

    async def get_ranking_list(self, *, op_id: str, page: int, per_page: int) -> PagedResult:
        return PagedResult(items=[], page=page, has_more=False)

    async def browse(self, state: BrowseState, *, per_page: int) -> PagedResult:
        return PagedResult(items=[], page=state.page, has_more=False)

    # ---- helpers ---------------------------------------------------------
    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get("", params=params)
        except httpx.HTTPError as exc:
            raise ApiError("Could not reach the movie service.", status_code=502) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiError("The movie service returned an invalid response.", status_code=response.status_code) from exc
        if isinstance(payload, dict) and payload.get("error"):
            msg = str(payload.get("error"))
            raise ApiError(
                msg,
                status_code=response.status_code,
                not_found="not found" in msg.lower(),
                rate_limited=response.status_code == 429,
            )
        if not response.is_success:
            raise ApiError(f"Request failed ({response.status_code}).", status_code=response.status_code)
        return payload if isinstance(payload, dict) else {"data": payload}

    def _parse_item(self, item: dict[str, Any]) -> SearchResult | None:
        subject_id = str(item.get("id") or item.get("subjectId") or "").strip()
        title = str(item.get("title") or "").strip()
        if not subject_id or not title:
            return None
        subject_type = 2 if str(item.get("type")) == "tv" else 1
        return SearchResult(
            subject_id=subject_id,
            title=title,
            year=str(item.get("year") or "")[:4],
            subject_type=subject_type,
            poster=str(item.get("poster") or ""),
            description=str(item.get("description") or item.get("overview") or ""),
            rating=str(item.get("rating") or ""),
        )

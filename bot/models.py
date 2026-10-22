from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha1
from typing import Any


class UserPlan(str, Enum):
    BASIC = "basic"
    PRO = "pro"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(slots=True)
class TelegramUserRecord:
    telegram_user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    plan: UserPlan = UserPlan.BASIC
    plan_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_seen_at: datetime | None = None

    @property
    def active_plan(self) -> UserPlan:
        # Full release: every user has full access (no PRO/basic tiers).
        return UserPlan.PRO

    @property
    def is_pro(self) -> bool:
        # Full release: all features unlocked for everyone.
        return True

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "TelegramUserRecord":
        plan_value = str(row.get("plan") or UserPlan.BASIC.value).lower()
        plan = UserPlan.PRO if plan_value == UserPlan.PRO.value else UserPlan.BASIC
        return cls(
            telegram_user_id=int(row["telegram_user_id"]),
            username=row.get("username"),
            first_name=row.get("first_name"),
            last_name=row.get("last_name"),
            plan=plan,
            plan_expires_at=parse_datetime(row.get("plan_expires_at")),
            created_at=parse_datetime(row.get("created_at")),
            updated_at=parse_datetime(row.get("updated_at")),
            last_seen_at=parse_datetime(row.get("last_seen_at")),
        )


@dataclass(slots=True)
class SearchResult:
    subject_id: str
    title: str
    year: str = ""
    subject_type: int = 0
    poster: str = ""
    detail_path: str = ""
    description: str = ""
    rating: str = ""

    @property
    def media_label(self) -> str:
        if self.subject_type == 1:
            return "Movie"
        if self.subject_type == 2:
            return "TV"
        return "Title"


@dataclass(slots=True)
class SeasonInfo:
    season_number: int
    max_episode: int


@dataclass(slots=True)
class MediaDetails:
    subject_id: str
    title: str
    subject_type: int
    year: str = ""
    rating: str = ""
    description: str = ""
    poster: str = ""
    genres: list[str] = field(default_factory=list)
    seasons: list[SeasonInfo] = field(default_factory=list)
    country_name: str = ""
    duration: str = ""
    release_date: str = ""
    imdb_votes: str = ""
    subtitles_summary: str = ""
    cast: list[str] = field(default_factory=list)

    @property
    def is_movie(self) -> bool:
        return self.subject_type == 1 or not self.seasons

    @property
    def media_label(self) -> str:
        return "Movie" if self.is_movie else "TV Show"


@dataclass(slots=True)
class SourceOption:
    quality: str
    download_url: str
    size: str = ""
    audio_label: str = ""
    audio_language: str = ""
    direct_url: str = ""
    stream_url: str = ""
    quality_num: int = 0
    is_dubbed: bool = False
    is_recommended: bool = False

    @property
    def variant_id(self) -> str:
        audio_key = self.audio_label or self.audio_language or "default"
        payload = f"{self.quality}|{audio_key}".encode("utf-8")
        return sha1(payload).hexdigest()[:8]

    @property
    def display_label(self) -> str:
        audio = self.audio_label or self.audio_language
        if audio:
            return f"{self.quality} - {audio}"
        return self.quality

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "SourceOption | None":
        download_url = str(payload.get("downloadUrl") or payload.get("download_url") or "").strip()
        quality = str(payload.get("quality") or payload.get("resolution") or "").strip()
        if not download_url or not quality:
            return None
        return cls(
            quality=quality,
            download_url=download_url,
            size=str(payload.get("size") or ""),
            audio_label=str(payload.get("audioLabel") or ""),
            audio_language=str(payload.get("audioLanguage") or ""),
            direct_url=str(payload.get("directUrl") or payload.get("url") or ""),
            stream_url=str(payload.get("streamUrl") or payload.get("stream_url") or ""),
            quality_num=int(payload.get("qualityNum") or 0),
            is_dubbed=bool(payload.get("isDubbed", False)),
            is_recommended=bool(payload.get("isRecommended", False)),
        )


@dataclass(slots=True)
class SubtitleOption:
    language_code: str
    language_name: str
    url: str
    size: str = ""

    @property
    def display_label(self) -> str:
        return self.language_name or self.language_code or "Subtitle"

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "SubtitleOption | None":
        url = str(payload.get("url") or payload.get("file") or "").strip()
        if not url:
            return None
        return cls(
            language_code=str(payload.get("lan") or payload.get("lang") or payload.get("language") or "").strip(),
            language_name=str(payload.get("lanName") or payload.get("langName") or payload.get("languageName") or "").strip(),
            url=url,
            size=str(payload.get("size") or payload.get("filesize") or "").strip(),
        )


@dataclass(slots=True)
class DiscoverySection:
    title: str
    op_id: str = ""
    source_url: str = ""
    items: list[SearchResult] = field(default_factory=list)


@dataclass(slots=True)
class PagedResult:
    items: list[SearchResult]
    page: int = 1
    has_more: bool = False
    total: int | None = None


@dataclass(slots=True)
class BrowseState:
    channel_id: int
    genre: str = "All"
    country: str = "All"
    year: str = "All"
    classify: str = "All"
    sort: str = "Hottest"
    page: int = 1

    @property
    def catalog_label(self) -> str:
        return "Movies" if self.channel_id == 1 else "TV"

    def payload(self, *, per_page: int) -> dict[str, Any]:
        return {
            "page": self.page,
            "perPage": per_page,
            "channelId": self.channel_id,
            "genre": self.genre or "All",
            "country": self.country or "All",
            "year": self.year or "All",
            "sort": self.sort or "Hottest",
            "classify": self.classify or "All",
        }

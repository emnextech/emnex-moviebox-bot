from aiogram.filters.callback_data import CallbackData


class MediaSelectCallback(CallbackData, prefix="md"):
    subject_id: str
    ref: str = ""


class MovieQualityCallback(CallbackData, prefix="mq"):
    subject_id: str
    variant: str


class TvSeasonCallback(CallbackData, prefix="ts"):
    subject_id: str
    season: int


class TvEpisodePageCallback(CallbackData, prefix="tp"):
    subject_id: str
    season: int
    page: int


class TvEpisodeCallback(CallbackData, prefix="te"):
    subject_id: str
    season: int
    episode: int


class TvEpisodeQualityCallback(CallbackData, prefix="tq"):
    subject_id: str
    season: int
    episode: int
    variant: str


class TvBulkSelectCallback(CallbackData, prefix="tb"):
    subject_id: str
    season: int
    page: int


class TvBulkQualityCallback(CallbackData, prefix="bk"):
    subject_id: str
    season: int
    page: int
    variant: str


class UpgradePromptCallback(CallbackData, prefix="up"):
    subject_id: str
    season: int = 0
    page: int = 0


class SourceRefreshCallback(CallbackData, prefix="rf"):
    subject_id: str
    variant: str
    season: int = 0
    episode: int = 0


class SubtitlePromptCallback(CallbackData, prefix="st"):
    subject_id: str
    variant: str
    season: int = 0
    episode: int = 0


class AnimeSimilarCallback(CallbackData, prefix="as"):
    subject_id: str


class HomeSectionCallback(CallbackData, prefix="hs"):
    token: str
    index: int


class DiscoveryPageCallback(CallbackData, prefix="dp"):
    token: str
    page: int


class BrowseCatalogCallback(CallbackData, prefix="bc"):
    channel_id: int


class BrowsePresetCallback(CallbackData, prefix="bp"):
    preset: str


class BrowseFilterOpenCallback(CallbackData, prefix="fo"):
    token: str
    field: str
    page: int = 0


class BrowseFilterSetCallback(CallbackData, prefix="fs"):
    token: str
    field: str
    index: int


class BrowseResetCallback(CallbackData, prefix="fr"):
    token: str

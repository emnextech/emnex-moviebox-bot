from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FilterOption:
    label: str
    value: str


GENRE_OPTIONS: tuple[FilterOption, ...] = (
    FilterOption("All", "All"),
    FilterOption("Action", "Action"),
    FilterOption("Adventure", "Adventure"),
    FilterOption("Animation", "Animation"),
    FilterOption("Biography", "Biography"),
    FilterOption("Comedy", "Comedy"),
    FilterOption("Crime", "Crime"),
    FilterOption("Documentary", "Documentary"),
    FilterOption("Drama", "Drama"),
    FilterOption("Family", "Family"),
    FilterOption("Fantasy", "Fantasy"),
    FilterOption("Film-Noir", "Film-Noir"),
    FilterOption("Game-Show", "Game-Show"),
    FilterOption("History", "History"),
    FilterOption("Horror", "Horror"),
    FilterOption("Music", "Music"),
    FilterOption("Musical", "Musical"),
    FilterOption("Mystery", "Mystery"),
    FilterOption("News", "News"),
    FilterOption("Reality-TV", "Reality-TV"),
    FilterOption("Romance", "Romance"),
    FilterOption("Sci-Fi", "Sci-Fi"),
    FilterOption("Short", "Short"),
    FilterOption("Sport", "Sport"),
    FilterOption("Talk-Show", "Talk-Show"),
    FilterOption("Thriller", "Thriller"),
    FilterOption("War", "War"),
    FilterOption("Western", "Western"),
    FilterOption("Other", "Other"),
)

COUNTRY_OPTIONS: tuple[FilterOption, ...] = (
    FilterOption("All", "All"),
    FilterOption("United States", "United States"),
    FilterOption("United Kingdom", "United Kingdom"),
    FilterOption("Korea", "Korea"),
    FilterOption("Japan", "Japan"),
    FilterOption("Bangladesh", "Bangladesh"),
    FilterOption("China", "China"),
    FilterOption("Egypt", "Egypt"),
    FilterOption("France", "France"),
    FilterOption("Germany", "Germany"),
    FilterOption("India", "India"),
    FilterOption("Indonesia", "Indonesia"),
    FilterOption("Iraq", "Iraq"),
    FilterOption("Italy", "Italy"),
    FilterOption("Ivory Coast", "Ivory Coast"),
    FilterOption("Kenya", "Kenya"),
    FilterOption("Lebanon", "Lebanon"),
    FilterOption("Mexico", "Mexico"),
    FilterOption("Morocco", "Morocco"),
    FilterOption("Nigeria", "Nigeria"),
    FilterOption("Pakistan", "Pakistan"),
    FilterOption("Philippines", "Philippines"),
    FilterOption("Russia", "Russia"),
    FilterOption("Saudi Arabia", "Saudi Arabia"),
    FilterOption("South Africa", "South Africa"),
    FilterOption("Spain", "Spain"),
    FilterOption("Syria", "Syria"),
    FilterOption("Thailand", "Thailand"),
    FilterOption("Turkey", "Turkey"),
    FilterOption("Other", "Other"),
)

YEAR_OPTIONS: tuple[FilterOption, ...] = (
    FilterOption("All", "All"),
    FilterOption("2025", "2025"),
    FilterOption("2024", "2024"),
    FilterOption("2023", "2023"),
    FilterOption("2022", "2022"),
    FilterOption("2021", "2021"),
    FilterOption("2020", "2020"),
    FilterOption("2010s", "2010s"),
    FilterOption("2000s", "2000s"),
    FilterOption("1990s", "1990s"),
    FilterOption("1980s", "1980s"),
    FilterOption("Other", "Other"),
)

LANGUAGE_OPTIONS: tuple[FilterOption, ...] = (
    FilterOption("All", "All"),
    FilterOption("French dub", "French dub"),
    FilterOption("Hindi dub", "Hindi dub"),
    FilterOption("Bengali dub", "Bengali dub"),
    FilterOption("Urdu dub", "Urdu dub"),
    FilterOption("Punjabi dub", "Punjabi dub"),
    FilterOption("Tamil dub", "Tamil dub"),
    FilterOption("Telugu dub", "Telugu dub"),
    FilterOption("Malayalam dub", "Malayalam dub"),
    FilterOption("Kannada dub", "Kannada dub"),
    FilterOption("Arabic dub", "Arabic dub"),
    FilterOption("Arabic sub", "Arabic sub"),
    FilterOption("Tagalog dub", "Tagalog dub"),
    FilterOption("Indonesian dub", "Indonesian dub"),
    FilterOption("Russian dub", "Russian dub"),
    FilterOption("Kurdish sub", "Kurdish sub"),
)

SORT_OPTIONS: tuple[FilterOption, ...] = (
    FilterOption("For You", "ForYou"),
    FilterOption("Hottest", "Hottest"),
    FilterOption("Latest", "Latest"),
    FilterOption("Rating", "Rating"),
)

FILTER_KEY_LABELS = {
    "g": "Genre",
    "c": "Country",
    "y": "Year",
    "l": "Language",
    "s": "Sort",
}

FILTER_OPTIONS = {
    "g": GENRE_OPTIONS,
    "c": COUNTRY_OPTIONS,
    "y": YEAR_OPTIONS,
    "l": LANGUAGE_OPTIONS,
    "s": SORT_OPTIONS,
}


def options_for(filter_key: str) -> tuple[FilterOption, ...]:
    return FILTER_OPTIONS.get(filter_key, ())


def label_for(filter_key: str) -> str:
    return FILTER_KEY_LABELS.get(filter_key, "Filter")

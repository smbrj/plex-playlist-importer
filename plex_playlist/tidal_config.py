from __future__ import annotations

from dataclasses import dataclass

from plex_playlist.tidal_matcher import DEFAULT_QUALITY_PREFERENCE


@dataclass(frozen=True)
class TidalQualityPreference:
    values: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def parse_quality_preference(raw: str | None) -> TidalQualityPreference:
    """
    Parse left-to-right TIDAL quality preference.

    Unknown values are retained so future TIDAL media tags can be configured
    without a code release. Empty/malformed configuration falls back to the
    built-in default.
    """
    if raw is None or not raw.strip():
        return TidalQualityPreference(DEFAULT_QUALITY_PREFERENCE)

    values: list[str] = []
    seen: set[str] = set()

    for token in raw.split(","):
        value = token.strip().upper()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)

    if not values:
        return TidalQualityPreference(
            DEFAULT_QUALITY_PREFERENCE,
            ("quality_preference was empty; using default",),
        )

    return TidalQualityPreference(tuple(values))

from __future__ import annotations

from dataclasses import dataclass
import re

from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import (
    TidalClient,
    TidalHydrationFailure,
    TidalTrackCandidate,
)
from plex_playlist.tidal_matcher import choose_tidal_match


_TRAILING_NUMERIC_PAREN_RE = re.compile(r"\s+\((?:\d{2}|\d{4})\)\s*$")


def tidal_requested_title(title: str) -> str:
    """
    Remove source-only trailing numeric metadata from TIDAL lookup titles.

    Examples:
        "Tootsee Roll (94)" -> "Tootsee Roll"
        "What I Got (1996)" -> "What I Got"

    This cleanup is intentionally TIDAL-specific. It does not modify the
    original playlist entry or the Plex/Lidarr matching pipeline.
    """
    return _TRAILING_NUMERIC_PAREN_RE.sub("", title).strip()



@dataclass(frozen=True)
class TidalResolution:
    matched: TidalTrackCandidate | None
    source: str  # "cache" or "api"
    search_title: str
    candidates: tuple[TidalTrackCandidate, ...] = ()
    hydration_failures: tuple[TidalHydrationFailure, ...] = ()

    @property
    def inconclusive(self) -> bool:
        return self.matched is None and bool(self.hydration_failures)


class TidalSearchService:
    """Resolve Plex-unmatched requests through TIDAL with optional TTL caching."""

    def __init__(
        self,
        *,
        client: TidalClient,
        cache: TidalSearchCache | None = None,
        artist_aliases: dict[str, str] | None = None,
        quality_preference: tuple[str, ...] | list[str] | None = None,
        allow_explicit: bool = True,
    ) -> None:
        self.client = client
        self.cache = cache
        self.artist_aliases = artist_aliases or {}
        self.quality_preference = quality_preference
        self.allow_explicit = bool(allow_explicit)

    def resolve(self, artist: str, title: str) -> TidalResolution:
        search_title = tidal_requested_title(title)

        if self.cache is not None:
            lookup = self.cache.get(
                artist,
                search_title,
                aliases=self.artist_aliases,
                allow_explicit=self.allow_explicit,
            )
            if lookup.found:
                return TidalResolution(
                    matched=lookup.matched,
                    source="cache",
                    search_title=search_title,
                    candidates=(),
                )

        candidates = self.client.search_tracks(artist, search_title)
        hydration_failures = tuple(
            getattr(self.client, "last_hydration_failures", ()) or ()
        )
        decision = choose_tidal_match(
            requested_artist=artist,
            requested_title=search_title,
            candidates=candidates,
            artist_aliases=self.artist_aliases,
            quality_preference=self.quality_preference,
            allow_explicit=self.allow_explicit,
        )

        if self.cache is not None:
            if decision.matched is not None:
                self.cache.put_match(
                    artist,
                    search_title,
                    decision.matched,
                    aliases=self.artist_aliases,
                    allow_explicit=self.allow_explicit,
                )
            elif not hydration_failures:
                self.cache.put_no_match(
                    artist,
                    search_title,
                    aliases=self.artist_aliases,
                    allow_explicit=self.allow_explicit,
                )

        return TidalResolution(
            matched=decision.matched,
            source="api",
            search_title=search_title,
            candidates=tuple(candidates),
            hydration_failures=hydration_failures,
        )

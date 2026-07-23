from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from plex_playlist.normalization import (
    canonical_artist_key,
    classify_version,
    normalize_title,
)
from plex_playlist.tidal_client import TidalTrackCandidate


ACCEPTABLE_STUDIO_VERSIONS = {
    "studio",
    "remaster",
    "mono",
    "stereo",
}


@dataclass(frozen=True)
class TidalMatchDecision:
    matched: TidalTrackCandidate | None
    reason: str


def is_acceptable_studio_recording(
    title: str,
    version: str = "",
) -> bool:
    version_text = " ".join(
        part for part in (title, version) if part
    )
    return classify_version(version_text) in ACCEPTABLE_STUDIO_VERSIONS


def qualifying_candidates(
    *,
    requested_artist: str,
    requested_title: str,
    candidates: list[TidalTrackCandidate],
    artist_aliases: Mapping[str, str] | None = None,
) -> list[TidalTrackCandidate]:
    aliases = artist_aliases or {}

    requested_artist_key = canonical_artist_key(
        requested_artist,
        aliases,
    )
    requested_title_key = normalize_title(requested_title)

    accepted: list[TidalTrackCandidate] = []

    for candidate in candidates:
        if not candidate.artist:
            continue

        candidate_artist_key = canonical_artist_key(
            candidate.artist,
            aliases,
        )
        if candidate_artist_key != requested_artist_key:
            continue

        if normalize_title(candidate.title) != requested_title_key:
            continue

        if not is_acceptable_studio_recording(
            candidate.title,
            candidate.version,
        ):
            continue

        accepted.append(candidate)

    return accepted


def choose_tidal_match(
    *,
    requested_artist: str,
    requested_title: str,
    candidates: list[TidalTrackCandidate],
    artist_aliases: Mapping[str, str] | None = None,
) -> TidalMatchDecision:
    accepted = qualifying_candidates(
        requested_artist=requested_artist,
        requested_title=requested_title,
        candidates=candidates,
        artist_aliases=artist_aliases,
    )

    if not accepted:
        return TidalMatchDecision(
            matched=None,
            reason="no exact studio match",
        )

    # Phase 1 deliberately does NOT invent a TIDAL quality ordering. Until a
    # live API response confirms the current quality fields/enums, preserve API
    # order. The quality tie-breaker will be activated after that validation.
    return TidalMatchDecision(
        matched=accepted[0],
        reason="exact artist/title studio match",
    )

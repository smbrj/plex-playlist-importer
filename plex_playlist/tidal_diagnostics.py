from __future__ import annotations

from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import tidal_candidate_rejection_reason


def format_tidal_search_results(
    *,
    requested_artist: str,
    requested_title: str,
    candidates: list[TidalTrackCandidate],
    accepted: list[TidalTrackCandidate],
    artist_aliases: dict[str, str] | None = None,
    allow_explicit: bool = True,
) -> str:
    """Format a sanitized, read-only TIDAL search diagnostic."""

    accepted_ids = {candidate.track_id for candidate in accepted}

    lines = [
        "",
        "TIDAL READ-ONLY SEARCH",
        f"Requested: {requested_artist} - {requested_title}",
        f"Candidates returned: {len(candidates)}",
        f"Strict matches: {len(accepted)}",
        "",
    ]

    if not candidates:
        lines.append("No TIDAL track candidates returned.")
        return "\n".join(lines)

    for number, candidate in enumerate(candidates, start=1):
        status = "ACCEPT" if candidate.track_id in accepted_ids else "REJECT"
        lines.extend(
            [
                f"[{number}] {status}",
                f"    Track ID : {candidate.track_id}",
                f"    Artist   : {candidate.artist or '<missing>'}",
                f"    Track    : {candidate.title or '<missing>'}",
                f"    Album    : {candidate.album or '<missing>'}",
                f"    Quality  : {candidate.quality or '<not exposed>'}",
                f"    Explicit : {'YES' if candidate.explicit else 'NO'}",
            ]
        )
        if status == "REJECT":
            reason = tidal_candidate_rejection_reason(
                requested_artist=requested_artist,
                requested_title=requested_title,
                candidate=candidate,
                artist_aliases=artist_aliases,
                allow_explicit=allow_explicit,
            )
            if reason:
                lines.append(f"    Reason   : {reason}")

    return "\n".join(lines)

from __future__ import annotations

from plex_playlist.tidal_client import TidalTrackCandidate


def format_tidal_search_results(
    *,
    requested_artist: str,
    requested_title: str,
    candidates: list[TidalTrackCandidate],
    accepted: list[TidalTrackCandidate],
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
            ]
        )

    return "\n".join(lines)

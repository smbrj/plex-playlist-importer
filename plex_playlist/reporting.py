#plex_playlist/reporting.py

"""
Reporting helpers for Plex Playlist Importer V2.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from plex_playlist.models import (
    ConfidenceLevel,
    LibraryTrack,
    MatchingSession,
)
# from plex_playlist.normalization import 
from plex_playlist.normalization import (
    normalize_artist,
    normalize_title,
    normalize_album,
    normalize_key,
    canonical_artist_key,
)

import re

_FILENAME_SEQUENCE_RE = re.compile(
    r"^\s*\d+\s*[.\-_)]+\s*"
)

logger = logging.getLogger("plex_playlist")

def _format_score(value: float) -> str:
    return f"{value:.1f}"

def write_unmatched_csv(
    session: MatchingSession,
    path: Path,
) -> None:
    """
    Write unmatched playlist entries to CSV.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "Sequence",
            "Artist",
            "Title",
            "Reason",
        ])

        for result in session.results:
            if result.matched is not None:
                continue

            writer.writerow([
                result.requested.sequence,
                result.requested.artist,
                result.requested.title,
                result.reason,
            ])


def log_match_summary(
    session: MatchingSession,
    artist_aliases: dict[str, str],
) -> None:
    """
    Log normal/fallback/unmatched match counts.
    """

    total = len(session.results)

    fallback = sum(
        1 for r in session.results
        if r.matched is not None
        and r.reason.startswith("Fallback")
    )

    normal = sum(
        1 for r in session.results
        if r.matched is not None
        and not r.reason.startswith("Fallback")
    )

    unmatched = sum(
        1 for r in session.results
        if r.matched is None
    )

    warnings = count_metadata_warnings(
        session,
        artist_aliases,
    )

    logger.info("")
    logger.info("--------------------------------------")
    logger.info("Matching summary:")
    logger.info("  Normal matches   : %d", normal)
    logger.info("  Fallback matches : %d", fallback)
    logger.info("  Unmatched        : %d", unmatched)
    logger.info("  Metadata Warnings: %d", warnings)
    logger.info("  Total            : %d", total)

    
def _match_type(result) -> str:
    if result.matched is None:
        return "Unmatched"

    if result.reason.startswith("Fallback"):
        return "Fallback"

    return result.confidence.name.title()

def write_match_report_csv(
    path: Path,
    session: MatchingSession,
    artist_aliases: dict[str, str],
    include_file_paths: bool = False,
) -> None:

    """
    Write a full match report for every playlist entry.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "Sequence",
            "Requested Artist",
            "Requested Title",

            "Matched Artist",
            "Matched Album Artist",
            "Matched Title",
            "Matched Album",

            "Matched Version",
            "Selected Version",

            "Rating Key",

            "Match Type",
            "Confidence",

            "Artist Score",
            "Title Score",
            "Album Artist Score",
            "Combined Score",
            "File Path",
            "Filename Artist",
            "Filename Title",
            "Metadata Warnings",
            "Reason",
        ])

        for result in session.results:
            matched = result.matched
            score = result.score

            selected_version = (
                matched.version
                if matched is not None
                else ""
            )
          
            filename_metadata = (
                _filename_artist_title(matched.file_path)
                if matched is not None
                else None
            )

            filename_artist = (
                filename_metadata[0]
                if filename_metadata is not None
                else ""
            )

            filename_title = (
                filename_metadata[1]
                if filename_metadata is not None
                else ""
            )

            
            writer.writerow([
                result.requested.sequence,
                result.requested.artist,
                result.requested.title,

                matched.artist if matched else "",
                matched.album_artist if matched else "",
                matched.title if matched else "",
                matched.album if matched else "",
                matched.version if matched else "",
                selected_version,
                matched.rating_key if matched else "",

                _match_type(result),
                result.confidence.name,

                _format_score(result.score.artist),
                _format_score(result.score.title),
                _format_score(result.score.album_artist),
                _format_score(result.score.combined),

                matched.file_path
                if matched and include_file_paths
                else "",

                filename_artist,
                filename_title,

                _metadata_warnings(
                    result,
                    artist_aliases,
                ),
                result.reason,
            ])

def _filename_stem(file_path: str) -> str:
    """
    Return a filename without its directory or final extension.

    Supports both Windows and Unix-style paths.
    """

    if not file_path:
        return ""

    normalized_path = file_path.replace("\\", "/")
    filename = normalized_path.rsplit("/", 1)[-1]

    if "." in filename:
        filename = filename.rsplit(".", 1)[0]

    return filename.strip()

def _clean_filename_stem(file_path: str) -> str:
    """
    Remove a leading track/sequence number from a filename.
    """

    stem = _filename_stem(file_path)

    return _FILENAME_SEQUENCE_RE.sub(
        "",
        stem,
    ).strip()

def _filename_artist_title(
    file_path: str,
) -> tuple[str, str] | None:
    """
    Parse filenames formatted as:

        Artist - Title.ext

    Filename metadata is diagnostic only.
    """

    stem = _clean_filename_stem(file_path)

    if not stem or " - " not in stem:
        return None

    artist, title = stem.split(" - ", 1)

    artist = artist.strip()
    title = title.strip()

    if not artist or not title:
        return None

    return artist, title

def _metadata_warnings(
    result,
    artist_aliases: dict[str, str],
) -> str:
    matched = result.matched

    if matched is None:
        return ""

    warnings: list[str] = []

    requested_artist = canonical_artist_key(
        result.requested.artist,
        artist_aliases,
    )

    matched_artist = canonical_artist_key(
        matched.artist,
        artist_aliases,
    )

    matched_album_artist = canonical_artist_key(
        matched.album_artist,
        artist_aliases,
    )

    various_artists = canonical_artist_key(
        "Various Artists",
        artist_aliases,
    )

    if matched_artist == various_artists:
        warnings.append("Matched artist is Various Artists")

    if matched_album_artist == various_artists:
        warnings.append("Matched album artist is Various Artists")

    if result.reason.startswith("Fallback"):
        warnings.append("Fallback match; verify artist metadata")

    if (
        matched_artist != requested_artist
        and matched_artist != various_artists
    ):
        warnings.append("Matched artist differs from requested artist")

    filename_metadata = (
        _filename_artist_title(result.matched.file_path)
        if result.matched is not None
        else None
    )

    filename_artist = (
        filename_metadata[0]
        if filename_metadata
        else ""
    )

    filename_title = (
        filename_metadata[1]
        if filename_metadata
        else ""
    )

    if filename_metadata is not None:
        filename_artist, filename_title = filename_metadata

        filename_artist_key = canonical_artist_key(
            filename_artist,
            artist_aliases,
        )

        plex_artist_key = canonical_artist_key(
            matched.artist,
            artist_aliases,
        )

        if (
            filename_artist_key
            and filename_artist_key != plex_artist_key
        ):
            warnings.append(
                "Filename artist differs from Plex artist"
            )

        filename_title_key = normalize_title(filename_title)
        plex_title_key = normalize_title(matched.title)

        if (
            filename_title_key
            and plex_title_key
            and filename_title_key != plex_title_key
        ):
            warnings.append(
                "Filename title differs from Plex title"
            )

    return "; ".join(warnings)

def count_metadata_warnings(
    session: MatchingSession,
    artist_aliases: dict[str, str],
) -> int:
    return sum(
        1
        for result in session.results
        if _metadata_warnings(result, artist_aliases)
    )

def _duplicate_type(group: list[LibraryTrack]) -> str:
    albums = {track.album for track in group if track.album}
    versions = {track.version for track in group if track.version}

    if len(albums) == 1 and len(versions) == 1:
        return "Same Album"

    if len(albums) > 1 and len(versions) == 1:
        return "Different Album"

    if len(versions) > 1:
        return "Different Version"

    return "Multiple Copies"


def write_duplicates_csv(
    tracks: list[LibraryTrack],
    path: Path,
) -> None:
    """
    Write duplicate logical tracks across the full Plex library.

    Duplicates are grouped by:
      normalized artist + normalized title + version
    """

    from collections import defaultdict
    from plex_playlist.normalization import normalize_key

    groups: dict[tuple[str, str, str], list[LibraryTrack]] = defaultdict(list)

    for track in tracks:
        key = (
            normalize_key(track.artist),
            normalize_key(track.title),
            track.version,
        )

        groups[key].append(track)

    duplicate_groups = [
        group
        for group in groups.values()
        if len(group) > 1
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "Artist",
            "Title",
            "Version",
            "Duplicate Type",
            "Likely Action",
            "Duplicate Count",
            "Album Count",
            "Duration Spread",
            "Rating Keys",
            "Albums",
            "Durations",
            "Years",
        ])

        for group in duplicate_groups:
            first = group[0]

            albums = sorted({t.album for t in group if t.album})
            durations = sorted({
                str(t.duration)
                for t in group
                if t.duration is not None
            })
            years = sorted({
                str(t.year)
                for t in group
                if t.year is not None
            })

            duplicate_type = _duplicate_type(group)

            duplicate_type_rank = {
                "Same Album": 0,
                "Multiple Copies": 1,
                "Different Version": 2,
                "Different Album": 3,
            }

            duplicate_groups.sort(
                key=lambda group: (
                    duplicate_type_rank.get(_duplicate_type(group), 99),
                    -len(group),
                    group[0].artist.lower(),
                    group[0].title.lower(),
                )
            )

            writer.writerow([
                first.artist,
                first.title,
                first.version,
                duplicate_type,
                _likely_duplicate_action(group),
                len(group),
                len(albums),
                _format_duration_spread(group),
                "; ".join(str(t.rating_key) for t in group),
                "; ".join(albums),
                "; ".join(durations),
                "; ".join(years),
            ])
            

def _likely_duplicate_action(group) -> str:

    duplicate_type = _duplicate_type(group)
    spread = _duration_spread(group)

    if duplicate_type == "Same Album":

        if spread <= 2000:
            return "Review/delete duplicate"

        if spread <= 10000:
            return "Review carefully"

        return "Inspect manually"

    if duplicate_type == "Different Version":
        return "Usually keep"

    if duplicate_type == "Different Album":
        return "Usually keep"

    return "Review"

def _duration_spread(group: list[LibraryTrack]) -> int:
    """
    Largest duration minus smallest duration in milliseconds.
    """

    durations = [
        track.duration
        for track in group
        if track.duration is not None
    ]

    if len(durations) < 2:
        return 0

    return max(durations) - min(durations)


def _format_duration_spread(group) -> str:
    """
    Human-readable duration spread.
    """

    spread = _duration_spread(group)

    return f"{spread} ms ({spread / 1000:.1f} s)"
"""
Playlist input parsers.

Supported formats:
- .txt : Artist - Title
- .csv : Artist,Title
- .tsv : Artist<TAB>Title
- .m3u : #EXTINF metadata containing Artist - Title

All parsers return PlaylistEntry objects.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from plex_playlist.models import PlaylistEntry
import re

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".csv",
    ".tsv",
    ".m3u",
    ".m3u8",
}

def _strip_track_number(value: str) -> str:
    """
    Remove a leading playlist sequence or track number.

    Examples:
        "1. Artist - Title"   -> "Artist - Title"
        "01 Artist - Title"   -> "Artist - Title"
        "001. Artist - Title" -> "Artist - Title"
    """

    return re.sub(
        r"^\s*\d+\s*[.)_-]?\s*",
        "",
        value,
    ).strip()       

def parse_playlist_file(
    path: str | Path,
) -> list[PlaylistEntry]:
    """
    Parse a supported playlist input file.

    The parser is selected from the input file extension.
    """

    source = Path(path)

    if not source.exists():
        raise FileNotFoundError(
            f"Playlist file not found: {source}"
        )

    if not source.is_file():
        raise ValueError(
            f"Playlist input is not a file: {source}"
        )

    extension = source.suffix.lower()

    parsers = {
        ".txt": parse_txt,
        ".csv": parse_csv,
        ".tsv": parse_tsv,
        ".m3u": parse_m3u,
        ".m3u8": parse_m3u,
    }

    parser = parsers.get(extension)

    if parser is None:
        supported = ", ".join(
            sorted(SUPPORTED_EXTENSIONS)
        )

        raise ValueError(
            f"Unsupported playlist format '{extension}'. "
            f"Supported formats: {supported}"
        )

    return parser(source)


def parse_txt(path: Path) -> list[PlaylistEntry]:
    """
    Parse plain-text playlist lines.

    Accepted formats:

        001. Artist - Title
        12 - Artist - Title
        Artist - Title

    Blank lines and lines without the required delimiter are ignored.
    """

    entries: list[PlaylistEntry] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            line = _strip_track_number(line)

            if " - " not in line:
                continue

            artist, title = line.split(" - ", 1)

            artist = artist.strip()
            title = title.strip()

            if not artist or not title:
                continue

            entries.append(
                PlaylistEntry(
                    sequence=len(entries) + 1,
                    artist=artist,
                    title=title,
                    line_number=line_number,
                    source=path,
                )
            )

    return entries


def parse_csv(path: Path) -> list[PlaylistEntry]:
    """
    Parse comma-separated input.

    Required fields:

        Artist,Title

    A header row is optional. Additional columns are ignored.
    """

    return _parse_delimited(
        path,
        delimiter=",",
    )


def parse_tsv(path: Path) -> list[PlaylistEntry]:
    """
    Parse tab-separated input.

    Required fields:

        Artist<TAB>Title

    A header row is optional. Additional columns are ignored.
    """

    return _parse_delimited(
        path,
        delimiter="\t",
    )


def _parse_delimited(
    path: Path,
    *,
    delimiter: str,
) -> list[PlaylistEntry]:
    """
    Shared CSV/TSV parser.
    """

    entries: list[PlaylistEntry] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(
            handle,
            delimiter=delimiter,
        )

        for line_number, row in enumerate(
            reader,
            start=1,
        ):
            if len(row) < 2:
                continue

            artist = row[0].strip()
            title = row[1].strip()

            if _is_artist_title_header(
                artist,
                title,
            ):
                continue

            if not artist or not title:
                continue

            entries.append(
                PlaylistEntry(
                    sequence=len(entries) + 1,
                    artist=artist,
                    title=title,
                    line_number=line_number,
                    source=path,
                )
            )

    return entries


def _is_artist_title_header(
    artist: str,
    title: str,
) -> bool:
    """
    Return True for a conventional Artist/Title header.
    """

    artist_header = artist.casefold() in {
        "artist",
        "requested artist",
    }

    title_header = title.casefold() in {
        "title",
        "track",
        "track title",
        "song",
        "song title",
        "requested title",
    }

    return artist_header and title_header


def parse_m3u(path: Path) -> list[PlaylistEntry]:
    """
    Parse extended M3U metadata lines.

    Supported entry form:

        #EXTINF:-1,Artist - Title
        /path/to/audio-file.flac

    Only #EXTINF metadata is used. Audio paths are not used for matching.
    """

    entries: list[PlaylistEntry] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            line = raw_line.strip()

            if not line.startswith("#EXTINF"):
                continue

            if "," not in line:
                continue

            metadata = line.split(",", 1)[1].strip()

            if " - " not in metadata:
                continue

            artist, title = metadata.split(
                " - ",
                1,
            )

            artist = artist.strip()
            title = title.strip()

            if not artist or not title:
                continue

            entries.append(
                PlaylistEntry(
                    sequence=len(entries) + 1,
                    artist=artist,
                    title=title,
                    line_number=line_number,
                    source=path,
                )
            )

    return entries


def validate_tracks(
    tracks: Iterable[PlaylistEntry],
) -> list[PlaylistEntry]:
    """
    Return entries containing both an artist and a title.

    This helper is retained for callers that perform separate validation.
    Individual parsers already enforce these requirements.
    """

    return [
        track
        for track in tracks
        if track.artist.strip()
        and track.title.strip()
    ]


def debug_print_tracks(
    tracks: Iterable[PlaylistEntry],
    limit: int = 10,
) -> None:
    """
    Print a small sample of parsed playlist entries.
    """

    for index, track in enumerate(tracks):
        if index >= limit:
            break

        print(
            f"{track.sequence}. "
            f"{track.artist} - {track.title}"
        )


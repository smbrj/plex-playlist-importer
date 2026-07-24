from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Protocol


class TidalReportCandidate(Protocol):
    track_id: str
    artist: str
    album: str
    title: str

REPORT_HEADER = ("tidal_url", "artist", "album", "track")


def tidal_track_url(track_id: str) -> str:
    value = str(track_id).strip()
    if not value:
        raise ValueError("TIDAL track ID must not be empty")
    return f"https://tidal.com/browse/track/{value}"


def timestamped_tidal_match_path(
    *,
    reports_directory: Path,
    now: datetime | None = None,
) -> Path:
    stamp = (now or datetime.now()).strftime("%m%d%H%M")
    return reports_directory / f"tidal-matched={stamp}.csv"


def write_tidal_matched_report(
    *,
    candidates: Iterable[TidalReportCandidate],
    reports_directory: Path,
    now: datetime | None = None,
) -> Path | None:
    unique: list[TidalReportCandidate] = []
    seen: set[str] = set()

    for candidate in candidates:
        track_id = str(candidate.track_id).strip()
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        unique.append(candidate)

    if not unique:
        return None

    reports_directory.mkdir(parents=True, exist_ok=True)
    output = timestamped_tidal_match_path(
        reports_directory=reports_directory,
        now=now,
    )

    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(REPORT_HEADER)
        for candidate in unique:
            writer.writerow(
                (
                    tidal_track_url(candidate.track_id),
                    candidate.artist,
                    candidate.album,
                    candidate.title,
                )
            )

    return output

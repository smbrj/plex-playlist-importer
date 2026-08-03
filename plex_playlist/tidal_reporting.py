from __future__ import annotations

from dataclasses import dataclass
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Protocol


class TidalReportCandidate(Protocol):
    track_id: str
    artist: str
    album: str
    title: str


@dataclass(frozen=True)
class TidalUnmatchedDiagnosticRow:
    requested_artist: str
    requested_title: str
    search_title: str
    search_source: str
    candidate_count: int
    candidate_number: int | None
    tidal_url: str
    candidate_artist: str
    candidate_title: str
    candidate_album: str
    candidate_quality: str
    available_candidate_qualities: str
    candidate_explicit: str
    decision: str
    rejection_reason: str


REPORT_HEADER = ("tidal_url", "artist", "album", "track")
UNMATCHED_REPORT_HEADER = (
    "requested_artist",
    "requested_title",
    "search_title",
    "search_source",
    "candidate_count",
    "candidate_number",
    "tidal_url",
    "candidate_artist",
    "candidate_title",
    "candidate_album",
    "candidate_quality",
    "available_candidate_qualities",
    "candidate_explicit",
    "decision",
    "rejection_reason",
)


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
    return reports_directory / f"tidal-matched-{stamp}.csv"


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


def timestamped_tidal_unmatched_path(
    *,
    reports_directory: Path,
    now: datetime | None = None,
) -> Path:
    stamp = (now or datetime.now()).strftime("%m%d%H%M")
    return reports_directory / f"tidal-unmatched-{stamp}.csv"


def _available_candidate_qualities(candidates: Iterable[object]) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        quality = str(getattr(candidate, "quality", "") or "").strip()
        for tag in quality.split(","):
            value = tag.strip()
            if value and value not in seen:
                seen.add(value)
                ordered.append(value)
    return " | ".join(ordered)


def build_tidal_unmatched_rows(
    *,
    requested_artist: str,
    requested_title: str,
    resolution: object,
    artist_aliases: Mapping[str, str] | None = None,
    allow_explicit: bool = True,
    rejected_terms: tuple[str, ...] | list[str] | None = None,
) -> list[TidalUnmatchedDiagnosticRow]:
    """Build diagnostic rows for one TIDAL resolution that did not match."""
    if getattr(resolution, "matched", None) is not None:
        return []

    source = str(getattr(resolution, "source", "") or "unknown")
    search_title = str(
        getattr(resolution, "search_title", requested_title) or requested_title
    )
    candidates = list(getattr(resolution, "candidates", ()) or ())
    available_qualities = _available_candidate_qualities(candidates)

    if source == "cache" and not candidates:
        return [
            TidalUnmatchedDiagnosticRow(
                requested_artist=requested_artist,
                requested_title=requested_title,
                search_title=search_title,
                search_source=source,
                candidate_count=0,
                candidate_number=None,
                tidal_url="",
                candidate_artist="",
                candidate_title="",
                candidate_album="",
                candidate_quality="",
                available_candidate_qualities="",
                candidate_explicit="",
                decision="CACHED_NO_MATCH",
                rejection_reason=(
                    "negative cache hit; candidate diagnostics not retained"
                ),
            )
        ]

    if not candidates:
        return [
            TidalUnmatchedDiagnosticRow(
                requested_artist=requested_artist,
                requested_title=requested_title,
                search_title=search_title,
                search_source=source,
                candidate_count=0,
                candidate_number=None,
                tidal_url="",
                candidate_artist="",
                candidate_title="",
                candidate_album="",
                candidate_quality="",
                available_candidate_qualities="",
                candidate_explicit="",
                decision="NO_CANDIDATES",
                rejection_reason="no TIDAL track candidates returned",
            )
        ]

    from plex_playlist.tidal_matcher import tidal_candidate_rejection_reason

    hydration_failures = {
        str(failure.track_id): str(failure.error)
        for failure in (getattr(resolution, "hydration_failures", ()) or ())
    }

    rows: list[TidalUnmatchedDiagnosticRow] = []
    for number, candidate in enumerate(candidates, start=1):
        hydration_error = hydration_failures.get(str(candidate.track_id))
        reason = tidal_candidate_rejection_reason(
            requested_artist=requested_artist,
            requested_title=search_title,
            candidate=candidate,
            artist_aliases=artist_aliases,
            allow_explicit=allow_explicit,
            rejected_terms=rejected_terms,
        )
        rows.append(
            TidalUnmatchedDiagnosticRow(
                requested_artist=requested_artist,
                requested_title=requested_title,
                search_title=search_title,
                search_source=source,
                candidate_count=len(candidates),
                candidate_number=number,
                tidal_url=(
                    tidal_track_url(candidate.track_id)
                    if str(candidate.track_id).strip()
                    else ""
                ),
                candidate_artist=candidate.artist or "",
                candidate_title=candidate.title or "",
                candidate_album=candidate.album or "",
                candidate_quality=candidate.quality or "",
                available_candidate_qualities=available_qualities,
                candidate_explicit="YES" if candidate.explicit else "NO",
                decision=(
                    "INCONCLUSIVE_HYDRATION"
                    if hydration_error
                    else "REJECT"
                ),
                rejection_reason=(
                    f"candidate hydration failed: {hydration_error}; "
                    "result not negative-cached"
                    if hydration_error
                    else (reason or "not selected")
                ),
            )
        )
    return rows


def write_tidal_unmatched_report(
    *,
    rows: Iterable[TidalUnmatchedDiagnosticRow],
    reports_directory: Path,
    now: datetime | None = None,
) -> Path | None:
    materialized = list(rows)
    if not materialized:
        return None

    reports_directory.mkdir(parents=True, exist_ok=True)
    output = timestamped_tidal_unmatched_path(
        reports_directory=reports_directory,
        now=now,
    )

    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(UNMATCHED_REPORT_HEADER)
        for row in materialized:
            writer.writerow(
                (
                    row.requested_artist,
                    row.requested_title,
                    row.search_title,
                    row.search_source,
                    row.candidate_count,
                    "" if row.candidate_number is None else row.candidate_number,
                    row.tidal_url,
                    row.candidate_artist,
                    row.candidate_title,
                    row.candidate_album,
                    row.candidate_quality,
                    row.available_candidate_qualities,
                    row.candidate_explicit,
                    row.decision,
                    row.rejection_reason,
                )
            )

    return output

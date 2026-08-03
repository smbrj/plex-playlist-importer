"""
Core data models used throughout Plex Playlist Manager.

These classes form the application's public contract.

Every module imports these models.

Python 3.11+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass, field




# ============================================================
# Enumerations
# ============================================================


class PlaylistMode(Enum):
    """Playlist update modes."""

    CREATE = auto()
    UPDATE = auto()
    REPLACE = auto()
    SYNC = auto()


class ConfidenceLevel(Enum):
    """Human readable match confidence."""

    NONE = auto()
    WEAK = auto()
    GOOD = auto()
    HIGH = auto()
    EXACT = auto()
    FALLBACK = auto()


# ============================================================
# Playlist Input
# ============================================================


@dataclass(slots=True, frozen=True)
class PlaylistEntry:
    """
    One parsed line from the playlist file.
    """

    sequence: int
    artist: str
    title: str

    line_number: int = 0

    source: Path | None = None


# ============================================================
# Plex Library
# ============================================================


@dataclass(slots=True, frozen=True)
class LibraryTrack:
    """
    One normalized Plex track.

    No PlexAPI objects are stored here.
    """

    rating_key: int

    guid: str | None

    artist: str

    album_artist: str

    album: str

    title: str

    duration: int | None

    year: int | None

    version: str = "studio"

    file_path: str = ""


# ============================================================
# Match Scoring
# ============================================================


@dataclass(slots=True, frozen=True)
class MatchScore:
    """
    Detailed fuzzy score breakdown.
    """

    artist: float

    album_artist: float

    title: float

    combined: float


# ============================================================
# Match Result
# ============================================================


@dataclass(slots=True)
class MatchResult:
    """
    Result returned from the matcher.
    """

    requested: PlaylistEntry

    matched: LibraryTrack | None

    score: MatchScore

    confidence: ConfidenceLevel

    reason: str = ""

    @property
    def matched_successfully(self) -> bool:
        return self.matched is not None

    @property
    def score_value(self) -> float:
        return self.score.combined

    @property
    def score_float(self) -> float:
        return self.score.combined


# ============================================================
# Matching Configuration
# ============================================================


@dataclass(slots=True)
class MatchingConfig:

    debug: bool = False
    trace: bool = False

    threshold: float = 85.0

    workers: int = 8

    artist_weight: float = 0.25

    album_artist_weight: float = 0.15

    title_weight: float = 0.45

    combined_weight: float = 0.15

    min_title_score: float = 95.0

    fallback_title_score: float = 80.0

    artist_aliases: dict[str, str] = field(default_factory=dict)

    rejected_terms: tuple[str, ...] = ()

    preferred_versions: list[str] = field(
    default_factory=lambda: [
        "studio",
        "remaster",
        "mono",
        "stereo",
        "single",
        "album",
        "live",
        "acoustic",
        "demo",
        "alternate",
        "instrumental",
        "radio",
        "extended",
        "edit",
    ]
)


# ============================================================
# Statistics
# ============================================================


@dataclass(slots=True)
class MatchingStatistics:

    requested: int = 0

    matched: int = 0

    unmatched: int = 0

    average_score: float = 0.0

    elapsed_seconds: float = 0.0


# ============================================================
# Cache
# ============================================================


@dataclass(slots=True)
class CacheStatistics:

    database: Path

    track_count: int

    size_mb: float

    last_refresh: str | None


# ============================================================
# Reports
# ============================================================


@dataclass(slots=True)
class ReportFiles:

    unmatched_csv: Path

    html_report: Path
    
    
# ============================================================
# Matching Session
# ============================================================


@dataclass(slots=True)
class MatchingSession:
    """
    Complete output of a matching run.
    """

    threshold: float = 85.0
    workers: int = 8

    results: list[MatchResult] = field(default_factory=list)

    elapsed_seconds: float = 0.0

    warnings: list[str] = field(default_factory=list)

    def build_stats(self) -> MatchingStatistics:
        return MatchingStatistics(
            requested=len(self.results),
            matched=len([r for r in self.results if r.matched is not None]),
            unmatched=len([r for r in self.results if r.matched is None]),
            elapsed_seconds=self.elapsed_seconds,
        )


# ============================================================
# V2 Compatibility Aliases
# ============================================================

InputTrack = PlaylistEntry
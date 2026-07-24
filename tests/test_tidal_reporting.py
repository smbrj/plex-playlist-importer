from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from plex_playlist.tidal_reporting import (
    REPORT_HEADER,
    tidal_track_url,
    timestamped_tidal_match_path,
    write_tidal_matched_report,
)


@dataclass(frozen=True)
class Candidate:
    track_id: str
    artist: str
    title: str
    album: str


def candidate(track_id, artist="Artist", title="Track", album="Album"):
    return Candidate(
        track_id=track_id,
        artist=artist,
        title=title,
        album=album,
    )


def test_tidal_track_url_uses_browse_track_page():
    assert tidal_track_url("123") == "https://tidal.com/browse/track/123"


def test_timestamped_filename_is_mmddhhmm(tmp_path: Path):
    path = timestamped_tidal_match_path(
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    )
    assert path.name == "tidal-matched=07232145.csv"


def test_no_matches_creates_no_report(tmp_path: Path):
    assert write_tidal_matched_report(
        candidates=[],
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    ) is None


def test_report_schema_and_values(tmp_path: Path):
    output = write_tidal_matched_report(
        candidates=[candidate("123", "Steely Dan", "Peg", "Aja")],
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    )
    assert output is not None
    lines = output.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == ",".join(REPORT_HEADER)
    assert lines[1] == "https://tidal.com/browse/track/123,Steely Dan,Aja,Peg"


def test_report_deduplicates_track_ids(tmp_path: Path):
    output = write_tidal_matched_report(
        candidates=[candidate("123"), candidate("123"), candidate("456")],
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    )
    assert output is not None
    assert len(output.read_text(encoding="utf-8-sig").splitlines()) == 3

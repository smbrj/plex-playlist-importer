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
    assert path.name == "tidal-matched-07232145.csv"


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


def test_unmatched_timestamped_filename_uses_dash(tmp_path: Path):
    from plex_playlist.tidal_reporting import timestamped_tidal_unmatched_path

    path = timestamped_tidal_unmatched_path(
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    )
    assert path.name == "tidal-unmatched-07232145.csv"


def test_unmatched_report_records_candidate_rejection_and_qualities(tmp_path: Path):
    from types import SimpleNamespace
    from plex_playlist.tidal_client import TidalTrackCandidate
    from plex_playlist.tidal_reporting import (
        UNMATCHED_REPORT_HEADER,
        build_tidal_unmatched_rows,
        write_tidal_unmatched_report,
    )

    candidates = (
        TidalTrackCandidate(
            track_id="111",
            artist="Wrong Artist",
            title="Peg",
            album="Album One",
            quality="HIRES_LOSSLESS,LOSSLESS",
        ),
        TidalTrackCandidate(
            track_id="222",
            artist="Steely Dan",
            title="Peg (Live)",
            album="Album Two",
            quality="LOSSLESS",
        ),
    )
    resolution = SimpleNamespace(
        matched=None,
        source="api",
        search_title="Peg",
        candidates=candidates,
    )

    rows = build_tidal_unmatched_rows(
        requested_artist="Steely Dan",
        requested_title="Peg",
        resolution=resolution,
    )
    assert len(rows) == 2
    assert rows[0].rejection_reason == "artist mismatch"
    assert rows[0].available_candidate_qualities == "HIRES_LOSSLESS | LOSSLESS"
    assert rows[1].rejection_reason == "non-studio recording"

    output = write_tidal_unmatched_report(
        rows=rows,
        reports_directory=tmp_path,
        now=datetime(2026, 7, 23, 21, 45),
    )
    assert output is not None
    lines = output.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == ",".join(UNMATCHED_REPORT_HEADER)
    assert "https://tidal.com/browse/track/111" in lines[1]
    assert "artist mismatch" in lines[1]


def test_unmatched_report_api_no_candidates(tmp_path: Path):
    from types import SimpleNamespace
    from plex_playlist.tidal_reporting import build_tidal_unmatched_rows

    rows = build_tidal_unmatched_rows(
        requested_artist="Missing",
        requested_title="Track",
        resolution=SimpleNamespace(
            matched=None,
            source="api",
            search_title="Track",
            candidates=(),
        ),
    )
    assert len(rows) == 1
    assert rows[0].decision == "NO_CANDIDATES"
    assert rows[0].candidate_count == 0


def test_unmatched_report_cached_no_match_is_explicit(tmp_path: Path):
    from types import SimpleNamespace
    from plex_playlist.tidal_reporting import build_tidal_unmatched_rows

    rows = build_tidal_unmatched_rows(
        requested_artist="Missing",
        requested_title="Track",
        resolution=SimpleNamespace(
            matched=None,
            source="cache",
            search_title="Track",
            candidates=(),
        ),
    )
    assert len(rows) == 1
    assert rows[0].decision == "CACHED_NO_MATCH"
    assert "candidate diagnostics not retained" in rows[0].rejection_reason


def test_unmatched_report_marks_hydration_failure_inconclusive():
    from types import SimpleNamespace
    from plex_playlist.tidal_client import TidalHydrationFailure, TidalTrackCandidate
    from plex_playlist.tidal_reporting import build_tidal_unmatched_rows

    candidate = TidalTrackCandidate(
        track_id="540307",
        artist="",
        title="Bark at the Moon",
        album="",
        quality="HIRES_LOSSLESS,LOSSLESS",
    )
    resolution = SimpleNamespace(
        matched=None,
        source="api",
        search_title="Bark At The Moon",
        candidates=(candidate,),
        hydration_failures=(
            TidalHydrationFailure(
                track_id="540307",
                error="TIDAL track detail failed with HTTP 503",
            ),
        ),
    )

    rows = build_tidal_unmatched_rows(
        requested_artist="Ozzy Osbourne",
        requested_title="Bark At The Moon",
        resolution=resolution,
    )

    assert len(rows) == 1
    assert rows[0].decision == "INCONCLUSIVE_HYDRATION"
    assert "HTTP 503" in rows[0].rejection_reason
    assert "not negative-cached" in rows[0].rejection_reason

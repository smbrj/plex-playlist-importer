from dataclasses import replace
from types import SimpleNamespace

from plex_playlist.lidarr_reporting import (
    LidarrDiagnosticRow,
    _decision_track_state,
    format_lidarr_summary,
    summarize_lidarr_diagnostics,
)


def row(*, artist: str, status: str) -> LidarrDiagnosticRow:
    return LidarrDiagnosticRow(
        sequence=1,
        requested_artist=artist,
        requested_title="Song",
        lidarr_status="",
        matched_lidarr_artist="",
        musicbrainz_artist_id="",
        lidarr_artist_id=None,
        already_managed=False,
        candidate_count=0,
        matched_album="",
        matched_track="",
        album_id=None,
        album_search_requested=False,
        album_search_command_id=None,
        album_search_status="",
        acquisition_status=status,
        track_id=None,
        track_found=False,
        track_file_available=False,
        recommended_action="",
        notes="",
    )


def test_summary_groups_operational_states() -> None:
    rows = [
        row(artist="Sam Cooke", status="TRACK_ALREADY_AVAILABLE"),
        row(artist="sam cooke", status="SEARCH_COMPLETED_FILE_AVAILABLE"),
        row(artist="Aretha Franklin", status="SEARCH_QUEUED"),
        row(artist="Marvin Gaye", status="SEARCH_RECENTLY_REQUESTED"),
        row(artist="Unknown", status="NO_ARTIST_CANDIDATE"),
        row(artist="Broken", status="REQUEST_FAILED"),
        row(artist="Review", status="SEARCH_NOT_REQUESTED"),
    ]

    summary = summarize_lidarr_diagnostics(rows)

    assert summary.tracks_checked == 7
    assert summary.unique_artists == 6
    assert summary.already_available == 1
    assert summary.newly_available == 1
    assert summary.searches_queued == 1
    assert summary.searches_suppressed == 1
    assert summary.no_lidarr_match == 1
    assert summary.request_failures == 1
    assert summary.other == 1


def test_zero_row_summary_is_readable() -> None:
    lines = format_lidarr_summary(summarize_lidarr_diagnostics([]))

    assert lines[0] == "Lidarr results"
    assert "Tracks checked       : 0" in lines
    assert "Unique artists       : 0" in lines
    assert not any("Other states" in line for line in lines)


def test_refreshed_resolution_is_canonical_track_state() -> None:
    original = SimpleNamespace(
        found_track={"id": 100},
        track_available=False,
    )
    refreshed = SimpleNamespace(
        found_track={"id": 200},
        track_available=True,
    )
    decision = SimpleNamespace(refreshed_resolution=refreshed)

    track, available = _decision_track_state(decision, original)

    assert track == {"id": 200}
    assert available is True


def test_legacy_direct_refreshed_fields_remain_supported() -> None:
    original = SimpleNamespace(
        found_track={"id": 100},
        track_available=False,
    )
    decision = SimpleNamespace(
        refreshed_track={"id": 200},
        refreshed_track_available=True,
    )

    track, available = _decision_track_state(decision, original)

    assert track == {"id": 200}
    assert available is True

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from plex_playlist.exceptions import LidarrError
from plex_playlist.lidarr_reporting import (
    build_lidarr_diagnostics,
    count_unique_unmatched_artists,
)


def unmatched(sequence: int, artist: str, title: str):
    return SimpleNamespace(
        entry=SimpleNamespace(
            sequence=sequence,
            artist=artist,
            title=title,
        ),
        matched=None,
        reason="No Plex match",
    )


def configured_client() -> Mock:
    client = Mock()
    client.lookup_artist.return_value = []
    client.get_managed_artist_by_mbid.return_value = None
    client.get_artist_albums.return_value = []
    client.get_artist_tracks.return_value = []
    return client


def test_lidarr_request_failure_isolated_per_entry() -> None:
    client = configured_client()
    client.lookup_artist.side_effect = [
        LidarrError("temporary 503"),
        [],
    ]

    rows = build_lidarr_diagnostics(
        results=[
            unmatched(1, "First Artist", "First Track"),
            unmatched(2, "Second Artist", "Second Track"),
        ],
        client=client,
    )

    assert len(rows) == 2
    assert rows[0].acquisition_status == "REQUEST_FAILED"
    assert rows[0].lidarr_status == "Lidarr request failed"
    assert "temporary 503" in rows[0].notes
    assert rows[1].lidarr_status == "No candidate"
    assert client.lookup_artist.call_count == 2


def test_progress_callback_reports_x_of_y() -> None:
    client = configured_client()
    progress: list[tuple[int, int, str]] = []

    build_lidarr_diagnostics(
        results=[
            unmatched(1, "Artist One", "Track One"),
            unmatched(2, "Artist Two", "Track Two"),
            unmatched(3, "Artist Three", "Track Three"),
        ],
        client=client,
        progress_callback=lambda done, total, entry: progress.append(
            (done, total, entry.artist)
        ),
    )

    assert progress == [
        (1, 3, "Artist One"),
        (2, 3, "Artist Two"),
        (3, 3, "Artist Three"),
    ]


def test_counts_unique_unmatched_artists_case_insensitively() -> None:
    results = [
        unmatched(1, "The Drifters", "One"),
        unmatched(2, " the   drifters ", "Two"),
        unmatched(3, "Sam Cooke", "Three"),
        SimpleNamespace(
            entry=SimpleNamespace(
                sequence=4,
                artist="Matched Artist",
                title="Four",
            ),
            matched=object(),
            reason="",
        ),
    ]

    assert count_unique_unmatched_artists(results) == 2

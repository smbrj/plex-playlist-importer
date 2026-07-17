from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from plex_playlist.lidarr_client import LidarrCommandStatus
from plex_playlist.lidarr_reporting import (
    SEARCH_COMPLETED_FILE_AVAILABLE,
    SEARCH_COMPLETED_NO_FILE,
    SEARCH_FAILED,
    SEARCH_QUEUED,
    build_lidarr_diagnostics,
    write_lidarr_diagnostic_csv,
)


def unmatched(sequence, artist, title, reason="No candidates"):
    return SimpleNamespace(
        entry=SimpleNamespace(
            sequence=sequence,
            artist=artist,
            title=title,
        ),
        matched=None,
        reason=reason,
    )


def artist(name, mbid="mbid-sam", lidarr_id=None):
    item = {"artistName": name, "foreignArtistId": mbid}
    if lidarr_id is not None:
        item["id"] = lidarr_id
    return item


def album(album_id, title):
    return {"id": album_id, "title": title}


def track(track_id, album_id, title, has_file=False):
    return {
        "id": track_id,
        "albumId": album_id,
        "title": title,
        "hasFile": has_file,
        "trackFileId": track_id if has_file else 0,
    }


def client_for_missing_track():
    client = Mock()
    client.lookup_artist.return_value = [artist("Sam Cooke")]
    client.get_managed_artist_by_mbid.return_value = artist(
        "Sam Cooke", lidarr_id=42
    )
    client.get_artist_albums.return_value = [album(100, "Shake")]
    client.get_artist_tracks.return_value = [
        track(200, 100, "Shake", has_file=False)
    ]
    client.search_album.return_value = {"id": 1234, "status": "queued"}
    return client


def test_search_queued_without_waiting() -> None:
    client = client_for_missing_track()
    rows = build_lidarr_diagnostics(
        results=[unmatched(1, "Sam Cooke", "Shake")],
        client=client,
        search_missing_albums=True,
    )
    assert rows[0].acquisition_status == SEARCH_QUEUED
    assert rows[0].album_search_requested is True
    client.wait_for_command.assert_not_called()


def test_completed_search_without_file_is_classified() -> None:
    client = client_for_missing_track()
    client.wait_for_command.return_value = LidarrCommandStatus(
        command_id=1234,
        name="AlbumSearch",
        status="completed",
        message="",
        completed=True,
        successful=True,
    )
    # Initial read: missing. Refresh after completed search: still missing.
    client.get_artist_tracks.side_effect = [
        [track(200, 100, "Shake", has_file=False)],
        [track(200, 100, "Shake", has_file=False)],
    ]
    rows = build_lidarr_diagnostics(
        results=[unmatched(1, "Sam Cooke", "Shake")],
        client=client,
        search_missing_albums=True,
        wait_for_search_seconds=30,
    )
    row = rows[0]
    assert row.acquisition_status == SEARCH_COMPLETED_NO_FILE
    assert row.track_file_available is False
    assert "TIDAL companion playlist" in row.recommended_action


def test_completed_search_with_file_is_classified() -> None:
    client = client_for_missing_track()
    client.wait_for_command.return_value = LidarrCommandStatus(
        command_id=1234,
        name="AlbumSearch",
        status="completed",
        message="",
        completed=True,
        successful=True,
    )
    client.get_artist_tracks.side_effect = [
        [track(200, 100, "Shake", has_file=False)],
        [track(200, 100, "Shake", has_file=True)],
    ]
    rows = build_lidarr_diagnostics(
        results=[unmatched(1, "Sam Cooke", "Shake")],
        client=client,
        search_missing_albums=True,
        wait_for_search_seconds=30,
    )
    assert rows[0].acquisition_status == SEARCH_COMPLETED_FILE_AVAILABLE
    assert rows[0].track_file_available is True


def test_failed_search_is_classified() -> None:
    client = client_for_missing_track()
    client.wait_for_command.return_value = LidarrCommandStatus(
        command_id=1234,
        name="AlbumSearch",
        status="failed",
        message="Indexer unavailable",
        completed=True,
        successful=False,
    )
    rows = build_lidarr_diagnostics(
        results=[unmatched(1, "Sam Cooke", "Shake")],
        client=client,
        search_missing_albums=True,
        wait_for_search_seconds=30,
    )
    assert rows[0].acquisition_status == SEARCH_FAILED
    assert rows[0].recommended_action == "Indexer unavailable"


def test_two_tracks_on_same_album_queue_once() -> None:
    client = client_for_missing_track()
    client.get_artist_tracks.return_value = [
        track(200, 100, "Shake"),
        track(201, 100, "Another Song"),
    ]
    rows = build_lidarr_diagnostics(
        results=[
            unmatched(1, "Sam Cooke", "Shake"),
            unmatched(2, "Sam Cooke", "Another Song"),
        ],
        client=client,
        search_missing_albums=True,
    )
    assert len(rows) == 2
    client.search_album.assert_called_once_with(100)
    assert rows[0].acquisition_status == SEARCH_QUEUED
    assert rows[1].acquisition_status == SEARCH_QUEUED


def test_csv_contains_acquisition_status(tmp_path: Path) -> None:
    client = client_for_missing_track()
    rows = build_lidarr_diagnostics(
        results=[unmatched(1, "Sam Cooke", "Shake")],
        client=client,
        search_missing_albums=True,
    )
    path = tmp_path / "lidarr.csv"
    write_lidarr_diagnostic_csv(rows, path)
    text = path.read_text(encoding="utf-8-sig")
    assert "Acquisition Status" in text
    assert SEARCH_QUEUED in text

from pathlib import Path
from unittest.mock import Mock
from plex_playlist.lidarr_acquisition import (
    LidarrAcquisitionService, LidarrResolution,
    SEARCH_QUEUED, SEARCH_RECENTLY_REQUESTED,
)
from plex_playlist.lidarr_search_history import LidarrSearchHistoryStore

def resolution() -> LidarrResolution:
    track = {"id": 9, "title": "Song", "albumId": 42, "hasFile": False}
    album = {"id": 42, "title": "Album"}
    return LidarrResolution(
        None, {"id": 7}, [], [album], [track],
        track, album, False, 7, 42,
    )

def test_recent_search_is_not_requeued(tmp_path: Path) -> None:
    store = LidarrSearchHistoryStore(tmp_path / "history.db")
    store.initialize()
    store.record_search(
        album_id=42, artist="Artist", album="Album",
        command_id=100, result=SEARCH_QUEUED,
    )
    client = Mock()
    service = LidarrAcquisitionService(
        client=client, history_store=store,
        remember_searches=True, retry_after_days=7,
    )
    decision = service.decide_search(
        requested_artist="Artist",
        resolution=resolution(),
        search_missing_albums=True,
    )
    assert decision.requested is False
    assert decision.acquisition_status == SEARCH_RECENTLY_REQUESTED
    client.search_album.assert_not_called()

def test_disabled_history_preserves_search_behavior() -> None:
    client = Mock()
    client.search_album.return_value = {"id": 200, "status": "queued"}
    service = LidarrAcquisitionService(
        client=client, history_store=None,
        remember_searches=False, retry_after_days=7,
    )
    decision = service.decide_search(
        requested_artist="Artist",
        resolution=resolution(),
        search_missing_albums=True,
    )
    assert decision.requested is True
    assert decision.acquisition_status == SEARCH_QUEUED

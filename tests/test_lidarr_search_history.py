from datetime import datetime, timedelta, timezone
from pathlib import Path
from plex_playlist.lidarr_search_history import LidarrSearchHistoryStore

def test_recent_search_is_blocked(tmp_path: Path) -> None:
    store = LidarrSearchHistoryStore(tmp_path / "history.db")
    store.initialize()
    now = datetime.now(timezone.utc)
    store.record_search(
        album_id=42, artist="Artist", album="Album",
        command_id=100, result="SEARCH_QUEUED", requested_at=now,
    )
    assert store.can_search(
        album_id=42, retry_after_days=7,
        now=now + timedelta(days=1),
    ) is False
    assert store.can_search(
        album_id=42, retry_after_days=7,
        now=now + timedelta(days=8),
    ) is True

def test_request_count_increments(tmp_path: Path) -> None:
    store = LidarrSearchHistoryStore(tmp_path / "history.db")
    store.initialize()
    for command_id in (100, 101):
        store.record_search(
            album_id=42, artist="Artist", album="Album",
            command_id=command_id, result="SEARCH_QUEUED",
        )
    entry = store.get(42)
    assert entry is not None
    assert entry.request_count == 2
    assert entry.last_command_id == 101

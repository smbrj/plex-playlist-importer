from datetime import datetime, timedelta, timezone
from pathlib import Path
from plex_playlist.cache import LibraryCache


def test_cache_age_and_staleness(tmp_path: Path) -> None:
    cache = LibraryCache(tmp_path / "cache.db")
    cache.initialize()
    refreshed = datetime.now(timezone.utc) - timedelta(hours=25)
    cache.set_metadata("last_successful_refresh", refreshed.isoformat())
    assert cache.cache_age_hours() is not None
    assert cache.is_stale(24) is True
    assert cache.is_stale(48) is False


def test_missing_refresh_is_stale(tmp_path: Path) -> None:
    cache = LibraryCache(tmp_path / "cache.db")
    cache.initialize()
    assert cache.last_refresh() is None
    assert cache.is_stale(24) is True

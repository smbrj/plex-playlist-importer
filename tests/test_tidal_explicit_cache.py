from datetime import datetime, timezone
import sqlite3
from pathlib import Path

from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import TidalTrackCandidate


def explicit_candidate() -> TidalTrackCandidate:
    return TidalTrackCandidate(
        track_id="123",
        artist="Test Artist",
        title="Test Song",
        album="Test Album",
        quality="DOLBY_ATMOS",
        explicit=True,
    )


def test_cache_round_trip_preserves_explicit_flag(tmp_path: Path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)

    cache.put_match(
        "Test Artist",
        "Test Song",
        explicit_candidate(),
        now=now,
        allow_explicit=True,
    )
    lookup = cache.get(
        "Test Artist",
        "Test Song",
        now=now,
        allow_explicit=True,
    )

    assert lookup.found is True
    assert lookup.matched is not None
    assert lookup.matched.explicit is True


def test_cache_keys_are_separated_by_explicit_policy(tmp_path: Path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)

    cache.put_no_match(
        "Test Artist",
        "Test Song",
        now=now,
        allow_explicit=False,
    )

    blocked = cache.get(
        "Test Artist",
        "Test Song",
        now=now,
        allow_explicit=False,
    )
    allowed = cache.get(
        "Test Artist",
        "Test Song",
        now=now,
        allow_explicit=True,
    )

    assert blocked.found is True
    assert blocked.matched is None
    assert allowed.found is False


def test_initialize_migrates_legacy_cache_with_explicit_column(tmp_path: Path):
    db = tmp_path / "tidal.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE tidal_search_cache (
                artist_key TEXT NOT NULL,
                title_key TEXT NOT NULL,
                status TEXT NOT NULL,
                track_id TEXT,
                artist TEXT,
                title TEXT,
                album TEXT,
                quality TEXT,
                version TEXT,
                cached_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (artist_key, title_key)
            )
            """
        )

    TidalSearchCache(db).initialize()

    with sqlite3.connect(db) as conn:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(tidal_search_cache)"
            ).fetchall()
        }
    assert "explicit" in columns

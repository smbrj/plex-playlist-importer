"""
SQLite cache for Plex library (V2).

Stores normalized LibraryTrack objects only.
Optimized for fast fuzzy matching.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from plex_playlist.models import LibraryTrack
from plex_playlist.normalization import (
    normalize_artist,
    normalize_title,
    normalize_album,
    normalize_key,
)

from datetime import datetime, timedelta, timezone
from plex_playlist.search_index import SearchIndex
from plex_playlist.normalization import classify_version

import logging

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 6


# ============================================================
# LibraryCache
# ============================================================

class LibraryCache:
    """
    SQLite-backed normalized Plex library cache.

    Responsibilities:
    - store Plex library metadata
    - provide fast retrieval for matcher
    - maintain normalization keys
    """

    def __init__(self, database: Path):

        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)


    # --------------------------------------------------------
    # Connection
    # --------------------------------------------------------

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:

        conn = sqlite3.connect(self.database)
        conn.row_factory = sqlite3.Row

        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --------------------------------------------------------
    # Schema
    # --------------------------------------------------------

    def initialize(self) -> None:

        schema = """
        CREATE TABLE IF NOT EXISTS tracks (
            rating_key INTEGER PRIMARY KEY,
            guid TEXT,

            artist TEXT,
            artist_key TEXT,

            album_artist TEXT,
            album_artist_key TEXT,

            album TEXT,
            album_key TEXT,

            title TEXT,
            title_key TEXT,

            duration INTEGER,
            year INTEGER,
            version TEXT NOT NULL DEFAULT 'studio',
            file_path TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_artist_key
        ON tracks(artist_key);

        CREATE INDEX IF NOT EXISTS idx_title_key
        ON tracks(title_key);

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.executescript(schema)

            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(tracks)")
            }

            if "file_path" not in columns:
                conn.execute(
                    """
                    ALTER TABLE tracks
                    ADD COLUMN file_path TEXT NOT NULL DEFAULT ''
                    """
                )

            conn.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    # --------------------------------------------------------
    # Write operations
    # --------------------------------------------------------

    def replace_tracks(self, tracks: list[LibraryTrack]) -> None:

        with self.connection() as conn:

            conn.execute("DELETE FROM tracks")

            conn.executemany(
                """
                INSERT INTO tracks (
                        rating_key,
                        guid,
                        artist,
                        artist_key,
                        album_artist,
                        album_artist_key,
                        album,
                        album_key,
                        title,
                        title_key,
                        duration,
                        year,
                        version,
                        file_path
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        t.rating_key,
                        t.guid,

                        t.artist,
                        normalize_key(t.artist),

                        t.album_artist,
                        normalize_key(t.album_artist),

                        t.album,
                        normalize_key(t.album),

                        t.title,
                        normalize_key(t.title),

                        t.duration,
                        t.year,
                        t.version,
                        t.file_path,
                    )
                    for t in tracks
                ],
            )

            

            # 🔥 IMPORTANT: metadata update MUST be inside same connection
            refreshed_at = datetime.now(timezone.utc).isoformat()
            metadata_rows = [
                ("last_refresh", refreshed_at),
                ("last_successful_refresh", refreshed_at),
                ("last_refresh_attempt", refreshed_at),
                ("last_refresh_result", "success"),
                ("track_count", str(len(tracks))),
            ]
            conn.executemany(
                """
                INSERT INTO metadata(key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                metadata_rows,
            )

        # --------------------------------------------------------
        # Read operations
        # --------------------------------------------------------

    def load_tracks(self) -> list[LibraryTrack]:
        """
        Load full library from cache.
        """

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            rows = conn.execute(
                """
                SELECT
                    rating_key,
                    guid,
                    artist,
                    album_artist,
                    album,
                    title,
                    duration,
                    year,
                    version,
                    file_path
                FROM tracks
                ORDER BY artist, title
                """
            ).fetchall()

        return [
            LibraryTrack(
                rating_key=row["rating_key"],
                guid=row["guid"],
                artist=row["artist"],
                album_artist=row["album_artist"],
                album=row["album"],
                title=row["title"],
                duration=row["duration"],
                year=row["year"],
                #version=classify_version(row["title"]),
                version=row["version"] if row["version"] else classify_version(row["title"]),
                file_path=(
                    row["file_path"]
                    if "file_path" in row.keys() and row["file_path"]
                    else ""
                ),
            )
            for row in rows
        ]

    def load_index(self) -> SearchIndex:
        """
        Load the cached Plex library and construct a SearchIndex.

        The SQLite database stores normalized metadata while the
        SearchIndex provides fast in-memory lookup structures for the
        matcher.
        """

        logger.info("Loading search index from SQLite")

        tracks = self.load_tracks()

        index = SearchIndex.build(tracks)

        logger.info(
            "Search index ready (%d tracks)",
            index.track_count,
        )

        return index

    # --------------------------------------------------------
    # Fast lookup helpers (for matcher)
    # --------------------------------------------------------

    def find_by_artist_key(self, artist: str) -> list[LibraryTrack]:
        """
        Fast lookup using normalized artist key.
        """

        key = normalize_key(artist)

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            rows = conn.execute(
                """
                SELECT *
                FROM tracks
                WHERE artist_key = ?
                """,
                (key,),
            ).fetchall()

        return [
            LibraryTrack(
                rating_key=row["rating_key"],
                guid=row["guid"],
                artist=row["artist"],
                album_artist=row["album_artist"],
                album=row["album"],
                title=row["title"],
                duration=row["duration"],
                year=row["year"],
                #version=classify_version(row["title"]),
               version=row["version"] if row["version"] else classify_version(row["title"]),
                file_path=(
                    row["file_path"]
                    if "file_path" in row.keys() and row["file_path"]
                    else ""
                ),
            )
            for row in rows
        ]

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    def set_metadata(self, key: str, value: str) -> None:

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            conn.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_metadata(self, key: str) -> str | None:

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            row = conn.execute(
                """
                SELECT value
                FROM metadata
                WHERE key = ?
                """,
                (key,),
            ).fetchone()

        return row["value"] if row else None

    # --------------------------------------------------------
    # Stats
    # --------------------------------------------------------

    def track_count(self) -> int:

        with self.connection() as conn:

            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            return conn.execute(
                "SELECT COUNT(*) FROM tracks"
            ).fetchone()[0]

    def is_empty(self):
         return self.track_count() == 0

    def contains_tracks(self) -> bool:
        """
        True if the cache contains at least one track.
        """

        return self.track_count() > 0

    def record_refresh_attempt(self, *, result: str, detail: str = "") -> None:
        attempted_at = datetime.now(timezone.utc).isoformat()
        self.set_metadata("last_refresh_attempt", attempted_at)
        self.set_metadata("last_refresh_result", result)
        if detail:
            self.set_metadata("last_refresh_detail", detail)

    def last_refresh(self) -> datetime | None:
        value = self.get_metadata("last_successful_refresh") or self.get_metadata("last_refresh")
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def cache_age_hours(self) -> float | None:
        refreshed_at = self.last_refresh()
        if refreshed_at is None:
            return None
        age = datetime.now(timezone.utc) - refreshed_at
        return max(0.0, age.total_seconds() / 3600.0)

    def is_stale(self, max_age_hours: float) -> bool:
        if max_age_hours <= 0:
            raise ValueError("max_age_hours must be greater than zero")
        age = self.cache_age_hours()
        return age is None or age > max_age_hours

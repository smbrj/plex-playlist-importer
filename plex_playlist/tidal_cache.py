from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from plex_playlist.normalization import canonical_artist_key, normalize_title
from plex_playlist.tidal_client import TidalTrackCandidate


@dataclass(frozen=True)
class TidalCacheLookup:
    found: bool
    matched: TidalTrackCandidate | None


class TidalSearchCache:
    """Disposable TTL cache for TIDAL MATCH and NO_MATCH search outcomes."""

    def __init__(
        self,
        database: str | Path,
        *,
        max_age_hours: float = 24.0,
    ) -> None:
        if max_age_hours <= 0:
            raise ValueError("TIDAL cache max_age_hours must be > 0")

        self.database = Path(database)
        self.max_age_hours = float(max_age_hours)

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tidal_search_cache (
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

    @staticmethod
    def _keys(
        artist: str,
        title: str,
        aliases: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        return (
            canonical_artist_key(artist, aliases or {}),
            normalize_title(title),
        )

    def get(
        self,
        artist: str,
        title: str,
        *,
        aliases: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> TidalCacheLookup:
        artist_key, title_key = self._keys(artist, title, aliases)
        now = now or datetime.now(timezone.utc)

        with sqlite3.connect(self.database) as conn:
            row = conn.execute(
                """
                SELECT status, track_id, artist, title, album, quality,
                       version, expires_at
                FROM tidal_search_cache
                WHERE artist_key = ? AND title_key = ?
                """,
                (artist_key, title_key),
            ).fetchone()

            if row is None:
                return TidalCacheLookup(found=False, matched=None)

            expires_at = datetime.fromisoformat(row[7])
            if expires_at <= now:
                conn.execute(
                    """
                    DELETE FROM tidal_search_cache
                    WHERE artist_key = ? AND title_key = ?
                    """,
                    (artist_key, title_key),
                )
                return TidalCacheLookup(found=False, matched=None)

        if row[0] == "NO_MATCH":
            return TidalCacheLookup(found=True, matched=None)

        return TidalCacheLookup(
            found=True,
            matched=TidalTrackCandidate(
                track_id=row[1] or "",
                artist=row[2] or "",
                title=row[3] or "",
                album=row[4] or "",
                quality=row[5],
                version=row[6] or "",
            ),
        )

    def put_match(
        self,
        requested_artist: str,
        requested_title: str,
        candidate: TidalTrackCandidate,
        *,
        aliases: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._put(
            requested_artist,
            requested_title,
            status="MATCH",
            candidate=candidate,
            aliases=aliases,
            now=now,
        )

    def put_no_match(
        self,
        requested_artist: str,
        requested_title: str,
        *,
        aliases: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._put(
            requested_artist,
            requested_title,
            status="NO_MATCH",
            candidate=None,
            aliases=aliases,
            now=now,
        )

    def _put(
        self,
        requested_artist: str,
        requested_title: str,
        *,
        status: str,
        candidate: TidalTrackCandidate | None,
        aliases: dict[str, str] | None,
        now: datetime | None,
    ) -> None:
        artist_key, title_key = self._keys(
            requested_artist,
            requested_title,
            aliases,
        )
        now = now or datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.max_age_hours)

        with sqlite3.connect(self.database) as conn:
            conn.execute(
                """
                INSERT INTO tidal_search_cache (
                    artist_key, title_key, status,
                    track_id, artist, title, album, quality, version,
                    cached_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artist_key, title_key) DO UPDATE SET
                    status = excluded.status,
                    track_id = excluded.track_id,
                    artist = excluded.artist,
                    title = excluded.title,
                    album = excluded.album,
                    quality = excluded.quality,
                    version = excluded.version,
                    cached_at = excluded.cached_at,
                    expires_at = excluded.expires_at
                """,
                (
                    artist_key,
                    title_key,
                    status,
                    candidate.track_id if candidate else None,
                    candidate.artist if candidate else None,
                    candidate.title if candidate else None,
                    candidate.album if candidate else None,
                    candidate.quality if candidate else None,
                    candidate.version if candidate else None,
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )

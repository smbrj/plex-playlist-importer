from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TidalTrackState:
    track_id: str
    artist: str
    title: str
    album: str
    favorite_added_by_ppi: bool
    first_seen: str
    last_seen: str


@dataclass(frozen=True)
class TidalCompanionMembership:
    playlist_name: str
    playlist_id: str
    track_id: str
    first_added: str
    last_seen: str


class TidalStateStore:
    """Persistent PPI ownership/state for TIDAL companion synchronization."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tidal_tracks (
                    track_id TEXT PRIMARY KEY,
                    artist TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '',
                    favorite_added_by_ppi INTEGER NOT NULL DEFAULT 0
                        CHECK (favorite_added_by_ppi IN (0, 1)),
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS companion_memberships (
                    playlist_name TEXT NOT NULL,
                    playlist_id TEXT NOT NULL,
                    track_id TEXT NOT NULL,
                    first_added TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    PRIMARY KEY (playlist_name, track_id),
                    FOREIGN KEY (track_id)
                        REFERENCES tidal_tracks(track_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_companion_track_id
                    ON companion_memberships(track_id);

                CREATE INDEX IF NOT EXISTS idx_companion_playlist_id
                    ON companion_memberships(playlist_id);
                """
            )
            conn.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_track(
        self,
        *,
        track_id: str,
        artist: str = "",
        title: str = "",
        album: str = "",
        favorite_added_by_ppi: bool = False,
    ) -> None:
        value = str(track_id).strip()
        if not value:
            raise ValueError("TIDAL track ID must not be empty")

        now = self._now()
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT favorite_added_by_ppi
                FROM tidal_tracks
                WHERE track_id = ?
                """,
                (value,),
            ).fetchone()

            # Ownership is sticky once PPI has added the favorite. Merely seeing
            # an already-favorited track on a later run must never erase that.
            prior_owned = bool(existing["favorite_added_by_ppi"]) if existing else False
            owned = prior_owned or bool(favorite_added_by_ppi)

            conn.execute(
                """
                INSERT INTO tidal_tracks(
                    track_id,
                    artist,
                    title,
                    album,
                    favorite_added_by_ppi,
                    first_seen,
                    last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(track_id) DO UPDATE SET
                    artist = CASE
                        WHEN excluded.artist <> '' THEN excluded.artist
                        ELSE tidal_tracks.artist
                    END,
                    title = CASE
                        WHEN excluded.title <> '' THEN excluded.title
                        ELSE tidal_tracks.title
                    END,
                    album = CASE
                        WHEN excluded.album <> '' THEN excluded.album
                        ELSE tidal_tracks.album
                    END,
                    favorite_added_by_ppi = excluded.favorite_added_by_ppi,
                    last_seen = excluded.last_seen
                """,
                (
                    value,
                    artist.strip(),
                    title.strip(),
                    album.strip(),
                    1 if owned else 0,
                    now,
                    now,
                ),
            )

    def record_membership(
        self,
        *,
        playlist_name: str,
        playlist_id: str,
        track_id: str,
    ) -> None:
        name = playlist_name.strip()
        pid = playlist_id.strip()
        tid = track_id.strip()
        if not name or not pid or not tid:
            raise ValueError(
                "playlist_name, playlist_id, and track_id are required"
            )

        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO companion_memberships(
                    playlist_name,
                    playlist_id,
                    track_id,
                    first_added,
                    last_seen
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(playlist_name, track_id) DO UPDATE SET
                    playlist_id = excluded.playlist_id,
                    last_seen = excluded.last_seen
                """,
                (name, pid, tid, now, now),
            )

    def set_favorite_ownership(
        self,
        *,
        track_id: str,
        owned_by_ppi: bool,
    ) -> None:
        value = str(track_id).strip()
        if not value:
            raise ValueError("TIDAL track ID must not be empty")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT track_id FROM tidal_tracks WHERE track_id = ?",
                (value,),
            ).fetchone()
            if row is None:
                raise ValueError(
                    f"TIDAL track {value} is not present in state database"
                )

            conn.execute(
                """
                UPDATE tidal_tracks
                SET favorite_added_by_ppi = ?
                WHERE track_id = ?
                """,
                (1 if owned_by_ppi else 0, value),
            )

    def get_track(self, track_id: str) -> TidalTrackState | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT track_id, artist, title, album,
                       favorite_added_by_ppi, first_seen, last_seen
                FROM tidal_tracks
                WHERE track_id = ?
                """,
                (track_id,),
            ).fetchone()

        if row is None:
            return None

        return TidalTrackState(
            track_id=row["track_id"],
            artist=row["artist"],
            title=row["title"],
            album=row["album"],
            favorite_added_by_ppi=bool(row["favorite_added_by_ppi"]),
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )

    def list_memberships_for_track(
        self,
        track_id: str,
    ) -> list[TidalCompanionMembership]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT playlist_name, playlist_id, track_id,
                       first_added, last_seen
                FROM companion_memberships
                WHERE track_id = ?
                ORDER BY playlist_name COLLATE NOCASE
                """,
                (track_id,),
            ).fetchall()

        return [
            TidalCompanionMembership(
                playlist_name=row["playlist_name"],
                playlist_id=row["playlist_id"],
                track_id=row["track_id"],
                first_added=row["first_added"],
                last_seen=row["last_seen"],
            )
            for row in rows
        ]

    def list_memberships_for_playlist(
        self,
        playlist_name: str,
    ) -> list[TidalCompanionMembership]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT playlist_name, playlist_id, track_id,
                       first_added, last_seen
                FROM companion_memberships
                WHERE playlist_name = ? COLLATE NOCASE
                ORDER BY track_id
                """,
                (playlist_name,),
            ).fetchall()

        return [
            TidalCompanionMembership(
                playlist_name=row["playlist_name"],
                playlist_id=row["playlist_id"],
                track_id=row["track_id"],
                first_added=row["first_added"],
                last_seen=row["last_seen"],
            )
            for row in rows
        ]

    def remove_membership(
        self,
        *,
        playlist_name: str,
        track_id: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM companion_memberships
                WHERE playlist_name = ? COLLATE NOCASE
                  AND track_id = ?
                """,
                (playlist_name, track_id),
            )

    def count_other_memberships_for_track(
        self,
        *,
        track_id: str,
        excluding_playlist_name: str,
    ) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM companion_memberships
                WHERE track_id = ?
                  AND playlist_name <> ? COLLATE NOCASE
                """,
                (track_id, excluding_playlist_name),
            ).fetchone()
        return int(row["count"])

    def count_memberships_for_track(self, track_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM companion_memberships
                WHERE track_id = ?
                """,
                (track_id,),
            ).fetchone()
        return int(row["count"])

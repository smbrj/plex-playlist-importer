from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


@dataclass(frozen=True, slots=True)
class XMPlaylistBackfillState:
    station_number: int
    station_name: str
    station_deeplink: str
    history_hours: int
    next_cursor: str | None
    oldest_timestamp: str | None
    backfill_complete: bool


class XMPlaylistStateStore:
    """SQLite persistence for bounded XMPlaylist backfill runs."""

    SCHEMA_VERSION = 2

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(station_state)"
                ).fetchall()
            }

            if columns and "history_hours" not in columns:
                connection.executescript(
                    """
                    DROP TABLE IF EXISTS tracks;
                    DROP TABLE IF EXISTS station_state;
                    """
                )

            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS station_state (
                    station_number INTEGER PRIMARY KEY,
                    station_name TEXT NOT NULL,
                    station_deeplink TEXT NOT NULL,
                    history_hours INTEGER NOT NULL,
                    next_cursor TEXT,
                    oldest_timestamp TEXT,
                    backfill_complete INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    station_number INTEGER NOT NULL,
                    artist_key TEXT NOT NULL,
                    title_key TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    title TEXT NOT NULL,
                    last_seen_timestamp TEXT NOT NULL,
                    PRIMARY KEY (
                        station_number,
                        artist_key,
                        title_key
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_tracks_station_timestamp
                    ON tracks(station_number, last_seen_timestamp);
                """
            )
            connection.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (str(self.SCHEMA_VERSION),),
            )

    def load_state(
        self,
        station_number: int,
    ) -> XMPlaylistBackfillState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    station_number,
                    station_name,
                    station_deeplink,
                    history_hours,
                    next_cursor,
                    oldest_timestamp,
                    backfill_complete
                FROM station_state
                WHERE station_number = ?
                """,
                (int(station_number),),
            ).fetchone()

        if row is None:
            return None

        return XMPlaylistBackfillState(
            station_number=int(row[0]),
            station_name=str(row[1]),
            station_deeplink=str(row[2]),
            history_hours=int(row[3]),
            next_cursor=str(row[4]) if row[4] is not None else None,
            oldest_timestamp=(
                str(row[5]) if row[5] is not None else None
            ),
            backfill_complete=bool(row[6]),
        )

    def save_state(
        self,
        state: XMPlaylistBackfillState,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO station_state(
                    station_number,
                    station_name,
                    station_deeplink,
                    history_hours,
                    next_cursor,
                    oldest_timestamp,
                    backfill_complete,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(station_number) DO UPDATE SET
                    station_name=excluded.station_name,
                    station_deeplink=excluded.station_deeplink,
                    history_hours=excluded.history_hours,
                    next_cursor=excluded.next_cursor,
                    oldest_timestamp=excluded.oldest_timestamp,
                    backfill_complete=excluded.backfill_complete,
                    updated_at=excluded.updated_at
                """,
                (
                    state.station_number,
                    state.station_name,
                    state.station_deeplink,
                    state.history_hours,
                    state.next_cursor,
                    state.oldest_timestamp,
                    1 if state.backfill_complete else 0,
                    updated_at,
                ),
            )

    def upsert_track(
        self,
        *,
        station_number: int,
        artist_key: str,
        title_key: str,
        artist: str,
        title: str,
        last_seen_timestamp: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tracks(
                    station_number,
                    artist_key,
                    title_key,
                    artist,
                    title,
                    last_seen_timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(station_number, artist_key, title_key)
                DO UPDATE SET
                    artist=excluded.artist,
                    title=excluded.title,
                    last_seen_timestamp=CASE
                        WHEN excluded.last_seen_timestamp >
                             tracks.last_seen_timestamp
                        THEN excluded.last_seen_timestamp
                        ELSE tracks.last_seen_timestamp
                    END
                """,
                (
                    int(station_number),
                    artist_key,
                    title_key,
                    artist,
                    title,
                    last_seen_timestamp,
                ),
            )

    def delete_before(
        self,
        *,
        station_number: int,
        cutoff_timestamp: str,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM tracks
                WHERE station_number = ?
                  AND last_seen_timestamp < ?
                """,
                (int(station_number), cutoff_timestamp),
            )
            return int(cursor.rowcount)

    def load_tracks(
        self,
        station_number: int,
    ) -> list[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT artist, title
                FROM tracks
                WHERE station_number = ?
                ORDER BY rowid
                """,
                (int(station_number),),
            ).fetchall()

        return [
            (str(row[0]), str(row[1]))
            for row in rows
        ]

    def reset_station(self, station_number: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM station_state WHERE station_number = ?",
                (int(station_number),),
            )
            connection.execute(
                "DELETE FROM tracks WHERE station_number = ?",
                (int(station_number),),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

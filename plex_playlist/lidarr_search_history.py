from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3


@dataclass(frozen=True, slots=True)
class LidarrSearchHistoryEntry:
    album_id: int
    artist: str
    album: str
    first_requested_utc: str
    last_requested_utc: str
    request_count: int
    last_command_id: int | None
    last_result: str


class LidarrSearchHistoryStore:
    SCHEMA_VERSION = 1

    def __init__(self, database: Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS search_history (
                    album_id INTEGER PRIMARY KEY,
                    artist TEXT NOT NULL,
                    album TEXT NOT NULL,
                    first_requested_utc TEXT NOT NULL,
                    last_requested_utc TEXT NOT NULL,
                    request_count INTEGER NOT NULL,
                    last_command_id INTEGER,
                    last_result TEXT NOT NULL
                );
            """)
            connection.execute(
                """INSERT INTO metadata(key, value)
                   VALUES('schema_version', ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (str(self.SCHEMA_VERSION),),
            )

    def get(self, album_id: int) -> LidarrSearchHistoryEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT album_id, artist, album, first_requested_utc,
                          last_requested_utc, request_count,
                          last_command_id, last_result
                   FROM search_history WHERE album_id = ?""",
                (int(album_id),),
            ).fetchone()
        if row is None:
            return None
        return LidarrSearchHistoryEntry(
            album_id=int(row[0]), artist=str(row[1]), album=str(row[2]),
            first_requested_utc=str(row[3]),
            last_requested_utc=str(row[4]),
            request_count=int(row[5]),
            last_command_id=int(row[6]) if row[6] is not None else None,
            last_result=str(row[7]),
        )

    def can_search(
        self,
        *,
        album_id: int,
        retry_after_days: float,
        now: datetime | None = None,
    ) -> bool:
        if retry_after_days < 0:
            raise ValueError("retry_after_days must be zero or greater")
        entry = self.get(album_id)
        if entry is None or retry_after_days == 0:
            return True
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        try:
            last_requested = datetime.fromisoformat(entry.last_requested_utc)
        except ValueError:
            return True
        if last_requested.tzinfo is None:
            last_requested = last_requested.replace(tzinfo=timezone.utc)
        return reference.astimezone(timezone.utc) - last_requested.astimezone(
            timezone.utc
        ) >= timedelta(days=retry_after_days)

    def record_search(
        self,
        *,
        album_id: int,
        artist: str,
        album: str,
        command_id: int | None,
        result: str,
        requested_at: datetime | None = None,
    ) -> None:
        timestamp = requested_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        value = timestamp.astimezone(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO search_history(
                       album_id, artist, album, first_requested_utc,
                       last_requested_utc, request_count,
                       last_command_id, last_result
                   ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                   ON CONFLICT(album_id) DO UPDATE SET
                       artist=excluded.artist,
                       album=excluded.album,
                       last_requested_utc=excluded.last_requested_utc,
                       request_count=search_history.request_count + 1,
                       last_command_id=excluded.last_command_id,
                       last_result=excluded.last_result""",
                (int(album_id), artist, album, value, value, command_id, result),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

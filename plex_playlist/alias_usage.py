from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AliasUsageEntry:
    alias: str
    target_artist: str
    use_count: int
    run_count: int
    first_used_utc: str | None
    last_used_utc: str | None
    last_source: str
    last_playlist: str


class AliasUsageStore:
    """Persistent aggregate usage history for configured artist aliases."""

    SCHEMA_VERSION = 1

    def __init__(self, database: Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS alias_usage (
                    alias TEXT PRIMARY KEY,
                    target_artist TEXT NOT NULL,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    first_used_utc TEXT,
                    last_used_utc TEXT,
                    last_source TEXT NOT NULL DEFAULT '',
                    last_playlist TEXT NOT NULL DEFAULT ''
                );
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

    def sync_aliases(self, aliases: dict[str, str]) -> None:
        """Ensure every configured alias has a durable usage row."""

        with self._connect() as connection:
            for alias, target in aliases.items():
                connection.execute(
                    """
                    INSERT INTO alias_usage(alias, target_artist)
                    VALUES (?, ?)
                    ON CONFLICT(alias) DO UPDATE SET
                        target_artist=excluded.target_artist
                    """,
                    (alias, target),
                )

    def record_run(
        self,
        *,
        usage_counts: dict[str, int],
        aliases: dict[str, str],
        source: str,
        playlist: str,
        used_at: datetime | None = None,
    ) -> None:
        self.sync_aliases(aliases)

        timestamp = used_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp_text = timestamp.astimezone(timezone.utc).isoformat()

        with self._connect() as connection:
            for alias, count in usage_counts.items():
                if count <= 0 or alias not in aliases:
                    continue

                connection.execute(
                    """
                    UPDATE alias_usage
                    SET
                        target_artist = ?,
                        use_count = use_count + ?,
                        run_count = run_count + 1,
                        first_used_utc = COALESCE(
                            first_used_utc,
                            ?
                        ),
                        last_used_utc = ?,
                        last_source = ?,
                        last_playlist = ?
                    WHERE alias = ?
                    """,
                    (
                        aliases[alias],
                        int(count),
                        timestamp_text,
                        timestamp_text,
                        source,
                        playlist,
                        alias,
                    ),
                )

    def get(self, alias: str) -> AliasUsageEntry | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    alias,
                    target_artist,
                    use_count,
                    run_count,
                    first_used_utc,
                    last_used_utc,
                    last_source,
                    last_playlist
                FROM alias_usage
                WHERE alias = ?
                """,
                (alias,),
            ).fetchone()

        return self._row_to_entry(row) if row is not None else None

    def list_entries(self) -> list[AliasUsageEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    alias,
                    target_artist,
                    use_count,
                    run_count,
                    first_used_utc,
                    last_used_utc,
                    last_source,
                    last_playlist
                FROM alias_usage
                ORDER BY alias COLLATE NOCASE
                """
            ).fetchall()

        return [self._row_to_entry(row) for row in rows]

    @staticmethod
    def classify(
        *,
        entry: AliasUsageEntry | None,
        target_exists: bool,
        review_after_days: float,
        now: datetime | None = None,
    ) -> str:
        if not target_exists:
            return "BROKEN"

        if entry is None or entry.use_count <= 0 or not entry.last_used_utc:
            return "UNUSED"

        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        try:
            last_used = datetime.fromisoformat(entry.last_used_utc)
        except ValueError:
            return "REVIEW"

        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=timezone.utc)

        if review_after_days <= 0:
            return "ACTIVE"

        dormant = reference.astimezone(timezone.utc) - last_used.astimezone(
            timezone.utc
        )
        return (
            "REVIEW"
            if dormant > timedelta(days=review_after_days)
            else "ACTIVE"
        )

    @staticmethod
    def _row_to_entry(row: sqlite3.Row | tuple) -> AliasUsageEntry:
        return AliasUsageEntry(
            alias=str(row[0]),
            target_artist=str(row[1]),
            use_count=int(row[2]),
            run_count=int(row[3]),
            first_used_utc=(
                str(row[4]) if row[4] is not None else None
            ),
            last_used_utc=(
                str(row[5]) if row[5] is not None else None
            ),
            last_source=str(row[6] or ""),
            last_playlist=str(row[7] or ""),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection


def count_alias_usage(
    *,
    results: Iterable[object],
    aliases: dict[str, str],
) -> dict[str, int]:
    """
    Count successful matches whose requested artist used an alias key.

    Matching is case-insensitive while preserving the configured alias key
    for persistence and reporting.
    """

    alias_lookup = {
        alias.casefold(): alias
        for alias in aliases
    }
    counts: dict[str, int] = {}

    for result in results:
        if getattr(result, "matched", None) is None:
            continue

        requested = (
            getattr(result, "requested", None)
            or getattr(result, "entry", None)
        )
        requested_artist = str(
            getattr(requested, "artist", "") or ""
        ).strip()
        configured_alias = alias_lookup.get(
            requested_artist.casefold()
        )
        if configured_alias is None:
            continue

        counts[configured_alias] = counts.get(configured_alias, 0) + 1

    return counts

#!/usr/bin/env python3
"""
Delete expired entries from PPI's disposable TIDAL search cache.

This script intentionally touches only the tidal_search_cache table.
It never modifies tidal_state.db or any ownership/membership state.
"""

from __future__ import annotations

import argparse
import configparser
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def resolve_cache_path(config_path: Path) -> Path:
    cfg = configparser.ConfigParser()
    loaded = cfg.read(config_path)
    if not loaded:
        raise RuntimeError(f"Configuration file not found: {config_path}")

    configured = Path(
        cfg.get(
            "tidal",
            "cache_database",
            fallback="cache/tidal_search_cache.db",
        ).strip()
        or "cache/tidal_search_cache.db"
    )

    if configured.is_absolute():
        return configured

    return config_path.resolve().parent / configured


def verify_schema(conn: sqlite3.Connection) -> None:
    table = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'tidal_search_cache'
        """
    ).fetchone()
    if table is None:
        raise RuntimeError("tidal_search_cache table not found; refusing cleanup")

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(tidal_search_cache)"
        ).fetchall()
    }
    if "expires_at" not in columns:
        raise RuntimeError(
            "tidal_search_cache.expires_at column not found; refusing cleanup"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove expired PPI TIDAL search-cache entries."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.ini"),
        help="PPI config file (default: config.ini)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report expired-row count without deleting anything",
    )
    parser.add_argument(
        "--vacuum",
        action="store_true",
        help="VACUUM the cache DB after deletion to reclaim free space",
    )
    args = parser.parse_args()

    try:
        database = resolve_cache_path(args.config)

        if not database.exists():
            print(f"TIDAL search cache does not exist; nothing to do: {database}")
            return 0

        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(database) as conn:
            verify_schema(conn)

            expired = conn.execute(
                """
                SELECT COUNT(*)
                FROM tidal_search_cache
                WHERE expires_at <= ?
                """,
                (now,),
            ).fetchone()[0]

            total = conn.execute(
                "SELECT COUNT(*) FROM tidal_search_cache"
            ).fetchone()[0]

            if args.dry_run:
                print(
                    f"TIDAL cache dry run: total={total}; "
                    f"expired={expired}; database={database}"
                )
                return 0

            conn.execute(
                """
                DELETE FROM tidal_search_cache
                WHERE expires_at <= ?
                """,
                (now,),
            )
            conn.commit()

            remaining = total - expired

            print(
                f"TIDAL cache cleanup: deleted={expired}; "
                f"remaining={remaining}; database={database}"
            )

            if args.vacuum:
                conn.execute("VACUUM")
                print("TIDAL cache VACUUM complete.")

        return 0

    except (OSError, sqlite3.Error, RuntimeError, configparser.Error) as exc:
        print(f"TIDAL cache cleanup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

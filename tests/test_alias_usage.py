from datetime import datetime, timedelta, timezone
from pathlib import Path

from plex_playlist.alias_usage import (
    AliasUsageStore,
    count_alias_usage,
)


class Requested:
    def __init__(self, artist: str) -> None:
        self.artist = artist


class Result:
    def __init__(self, artist: str, matched: object | None) -> None:
        self.requested = Requested(artist)
        self.matched = matched


def test_alias_usage_is_persisted(tmp_path: Path) -> None:
    store = AliasUsageStore(tmp_path / "usage.db")
    store.initialize()

    aliases = {
        "Doobie Brothers": "The Doobie Brothers",
        "Hollies": "The Hollies",
    }
    counts = count_alias_usage(
        results=[
            Result("Doobie Brothers", object()),
            Result("Doobie Brothers", object()),
            Result("Hollies", None),
        ],
        aliases=aliases,
    )

    store.record_run(
        usage_counts=counts,
        aliases=aliases,
        source="XMPlaylist Ch 14",
        playlist="Ch 14 - The Bridge",
    )

    entry = store.get("Doobie Brothers")
    assert entry is not None
    assert entry.use_count == 2
    assert entry.run_count == 1
    assert entry.last_source == "XMPlaylist Ch 14"

    unused = store.get("Hollies")
    assert unused is not None
    assert unused.use_count == 0


def test_alias_status_rules(tmp_path: Path) -> None:
    store = AliasUsageStore(tmp_path / "usage.db")
    store.initialize()
    now = datetime.now(timezone.utc)

    store.record_run(
        usage_counts={"Rolling Stones": 1},
        aliases={"Rolling Stones": "The Rolling Stones"},
        source="test",
        playlist="test",
        used_at=now - timedelta(days=120),
    )
    entry = store.get("Rolling Stones")

    assert AliasUsageStore.classify(
        entry=None,
        target_exists=True,
        review_after_days=90,
        now=now,
    ) == "UNUSED"

    assert AliasUsageStore.classify(
        entry=entry,
        target_exists=False,
        review_after_days=90,
        now=now,
    ) == "BROKEN"

    assert AliasUsageStore.classify(
        entry=entry,
        target_exists=True,
        review_after_days=90,
        now=now,
    ) == "REVIEW"

    assert AliasUsageStore.classify(
        entry=entry,
        target_exists=True,
        review_after_days=180,
        now=now,
    ) == "ACTIVE"

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from plex_playlist.xmplaylist_client import (
    XMPlaylistHistoryPage,
    XMPlaylistPlay,
    XMPlaylistStation,
)
from plex_playlist.xmplaylist_source import ingest_station
from plex_playlist.xmplaylist_state import XMPlaylistStateStore

STATION = XMPlaylistStation(
    id="station-14", number=14, name="The Bridge", deeplink="thebridge"
)


def fixed_now():
    return datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)


def play(number: int) -> XMPlaylistPlay:
    return XMPlaylistPlay(
        id=str(number),
        timestamp="2026-07-15T11:00:00Z",
        track_id=f"track-{number}",
        title=f"Song {number}",
        artists=(f"Artist {number}",),
    )


def page(start: int, cursor: str | None):
    return XMPlaylistHistoryPage(
        station=STATION,
        next_cursor=cursor,
        plays=tuple(play(i) for i in range(start, start + 3)),
    )


def test_max_tracks_pages_within_one_execution(tmp_path: Path) -> None:
    client = Mock()
    client.resolve_station.return_value = STATION
    client.get_history_page.side_effect = [
        page(1, "cursor-2"),
        page(4, "cursor-3"),
        page(7, "cursor-4"),
    ]

    result = ingest_station(
        client=client,
        station_number=14,
        hours=24,
        max_requests=10,
        max_tracks=7,
        state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
        now_factory=fixed_now,
    )

    assert len(result.entries) == 7
    assert client.get_history_page.call_count == 3
    assert result.requests_made == 4
    assert result.partial is False
    assert result.next_cursor == "cursor-4"


def test_max_tracks_deduplicates_before_counting(tmp_path: Path) -> None:
    client = Mock()
    client.resolve_station.return_value = STATION
    duplicate = play(1)
    client.get_history_page.side_effect = [
        XMPlaylistHistoryPage(
            station=STATION,
            next_cursor="cursor-2",
            plays=(duplicate, play(2), play(3)),
        ),
        XMPlaylistHistoryPage(
            station=STATION,
            next_cursor="cursor-3",
            plays=(duplicate, play(4), play(5)),
        ),
    ]

    result = ingest_station(
        client=client,
        station_number=14,
        hours=24,
        max_requests=5,
        max_tracks=5,
        state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
        now_factory=fixed_now,
    )

    assert len(result.entries) == 5
    assert client.get_history_page.call_count == 2


def test_omitted_max_tracks_preserves_existing_behavior(tmp_path: Path) -> None:
    client = Mock()
    client.resolve_station.return_value = STATION
    client.get_history_page.return_value = page(1, None)

    result = ingest_station(
        client=client,
        station_number=14,
        hours=24,
        max_requests=5,
        state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
        now_factory=fixed_now,
    )

    assert len(result.entries) == 3
    assert result.backfill_complete is True


def test_rejects_invalid_max_tracks() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        ingest_station(
            client=Mock(),
            station_number=14,
            max_tracks=0,
            now_factory=fixed_now,
        )

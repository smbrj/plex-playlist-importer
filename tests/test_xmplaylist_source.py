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
    id="station-14",
    number=14,
    name="The Bridge",
    deeplink="thebridge",
)


def play(play_id, timestamp, artist, title):
    return XMPlaylistPlay(
        id=play_id,
        timestamp=timestamp,
        track_id=f"track-{play_id}",
        title=title,
        artists=(artist,),
    )


def fixed_now():
    return datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)


def test_request_budget_is_never_exceeded(tmp_path: Path) -> None:
    client = Mock()
    client.resolve_station.return_value = STATION
    client.get_history_page.side_effect = [
        XMPlaylistHistoryPage(
            station=STATION,
            next_cursor=f"cursor-{index + 1}",
            plays=(
                play(
                    str(index),
                    "2026-07-15T11:00:00Z",
                    "Artist",
                    f"Song {index}",
                ),
            ),
        )
        for index in range(20)
    ]

    result = ingest_station(
        client=client,
        station_number=14,
        hours=8,
        max_requests=5,
        state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
        now_factory=fixed_now,
    )

    assert result.requests_made == 5
    assert client.get_history_page.call_count == 4
    assert result.partial is True
    assert result.next_cursor == "cursor-4"


def test_backfill_resumes_from_saved_cursor(tmp_path: Path) -> None:
    store = XMPlaylistStateStore(tmp_path / "xm.db")

    client1 = Mock()
    client1.resolve_station.return_value = STATION
    client1.get_history_page.side_effect = [
        XMPlaylistHistoryPage(
            station=STATION,
            next_cursor="cursor-2",
            plays=(
                play("1", "2026-07-15T11:00:00Z", "America", "Ventura Highway"),
            ),
        ),
    ]

    first = ingest_station(
        client=client1,
        station_number=14,
        hours=8,
        max_requests=2,
        state_store=store,
        now_factory=fixed_now,
    )
    assert first.next_cursor == "cursor-2"

    client2 = Mock()
    client2.resolve_station.return_value = STATION
    client2.get_history_page.return_value = XMPlaylistHistoryPage(
        station=STATION,
        next_cursor=None,
        plays=(
            play("2", "2026-07-15T10:00:00Z", "Eagles", "Take It Easy"),
        ),
    )

    second = ingest_station(
        client=client2,
        station_number=14,
        hours=8,
        max_requests=2,
        state_store=store,
        now_factory=fixed_now,
    )

    client2.get_history_page.assert_called_once_with(
        STATION,
        last="cursor-2",
    )
    assert second.backfill_complete is True
    assert [(e.artist, e.title) for e in second.entries] == [
        ("America", "Ventura Highway"),
        ("Eagles", "Take It Easy"),
    ]


def test_window_change_resets_saved_state(tmp_path: Path) -> None:
    store = XMPlaylistStateStore(tmp_path / "xm.db")

    client = Mock()
    client.resolve_station.return_value = STATION
    client.get_history_page.return_value = XMPlaylistHistoryPage(
        station=STATION,
        next_cursor=None,
        plays=(
            play("1", "2026-07-15T11:00:00Z", "America", "Ventura Highway"),
        ),
    )

    ingest_station(
        client=client,
        station_number=14,
        hours=3,
        max_requests=2,
        state_store=store,
        now_factory=fixed_now,
    )

    client.reset_mock()
    client.resolve_station.return_value = STATION
    client.get_history_page.return_value = XMPlaylistHistoryPage(
        station=STATION,
        next_cursor=None,
        plays=(
            play("2", "2026-07-15T10:00:00Z", "Eagles", "Take It Easy"),
        ),
    )

    result = ingest_station(
        client=client,
        station_number=14,
        hours=8,
        max_requests=2,
        state_store=store,
        now_factory=fixed_now,
    )

    assert [(e.artist, e.title) for e in result.entries] == [
        ("Eagles", "Take It Easy"),
    ]


@pytest.mark.parametrize("max_requests", [0, 1])
def test_rejects_too_small_request_budget(
    tmp_path: Path,
    max_requests: int,
) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        ingest_station(
            client=Mock(),
            station_number=14,
            hours=8,
            max_requests=max_requests,
            state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
            now_factory=fixed_now,
        )


@pytest.mark.parametrize("hours", [0, 721])
def test_rejects_invalid_history_window(
    tmp_path: Path,
    hours: int,
) -> None:
    with pytest.raises(ValueError, match="between 1 and 720"):
        ingest_station(
            client=Mock(),
            station_number=14,
            hours=hours,
            max_requests=2,
            state_store=XMPlaylistStateStore(tmp_path / "xm.db"),
            now_factory=fixed_now,
        )

from unittest.mock import Mock

import pytest

from plex_playlist.xmplaylist_client import (
    XMPlaylistClient,
    XMPlaylistError,
    XMPlaylistStation,
)


def response(payload, *, status_code=200, headers=None):
    item = Mock()
    item.status_code = status_code
    item.headers = headers or {}
    item.content = b"json"
    item.json.return_value = payload
    item.raise_for_status.return_value = None
    return item


def test_resolve_station_by_channel_number() -> None:
    client = XMPlaylistClient()
    client.session = Mock()
    client.session.request.return_value = response({
        "count": 1,
        "next": None,
        "previous": None,
        "results": [{
            "id": "station-14",
            "name": "The Bridge",
            "number": "14",
            "deeplink": "thebridge",
        }],
    })

    station = client.resolve_station(14)

    assert station == XMPlaylistStation(
        id="station-14",
        number=14,
        name="The Bridge",
        deeplink="thebridge",
    )
    assert station.plex_playlist_name == "Ch 14 - The Bridge"


def test_history_page_parses_tracks_and_cursor() -> None:
    client = XMPlaylistClient()
    client.session = Mock()
    client.session.request.return_value = response({
        "count": 1,
        "next": (
            "https://xmplaylist.com/api/station/thebridge"
            "?last=1712536800000"
        ),
        "previous": None,
        "channel": {
            "id": "station-14",
            "name": "The Bridge",
            "number": "14",
            "deeplink": "thebridge",
        },
        "results": [{
            "id": "play-1",
            "timestamp": "2026-07-15T12:00:00.000Z",
            "track": {
                "id": "track-1",
                "title": "Dreams",
                "artists": ["Fleetwood Mac"],
            },
        }],
    })

    page = client.get_history_page(
        XMPlaylistStation(
            id="station-14",
            number=14,
            name="The Bridge",
            deeplink="thebridge",
        )
    )

    assert page.next_cursor == "1712536800000"
    assert page.plays[0].title == "Dreams"
    assert page.plays[0].artists == ("Fleetwood Mac",)


def test_rate_limit_is_clear() -> None:
    client = XMPlaylistClient()
    client.session = Mock()
    client.session.request.return_value = response(
        {},
        status_code=429,
        headers={"Retry-After": "60"},
    )

    with pytest.raises(XMPlaylistError, match="retry after 60 seconds"):
        client.get_stations()

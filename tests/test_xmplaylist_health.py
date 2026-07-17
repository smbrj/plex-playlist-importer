from unittest.mock import Mock

from plex_playlist.xmplaylist_client import XMPlaylistClient


def response(payload):
    item = Mock()
    item.status_code = 200
    item.headers = {}
    item.content = b"json"
    item.json.return_value = payload
    item.raise_for_status.return_value = None
    return item


def test_health_check_reuses_station_discovery() -> None:
    client = XMPlaylistClient()
    client.session = Mock()
    client.session.request.return_value = response({
        "results": [{
            "id": "station-14",
            "name": "The Bridge",
            "number": "14",
            "deeplink": "thebridge",
        }],
    })

    health = client.is_available()
    station = client.resolve_station(14)

    assert health.available is True
    assert station.name == "The Bridge"
    assert client.session.request.call_count == 1

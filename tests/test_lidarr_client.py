from unittest.mock import Mock, patch

from plex_playlist.lidarr_client import LidarrClient


def make_client(response_payload):
    session = Mock()
    session.headers = {}
    response = Mock()
    response.content = b"json"
    response.raise_for_status.return_value = None
    response.json.return_value = response_payload
    session.request.return_value = response
    client = LidarrClient("http://lidarr.test", "test-api-key")
    client.session = session
    return client, session


def test_get_managed_artist_by_mbid() -> None:
    client, session = make_client([{
        "artistName": "Sam Cooke",
        "foreignArtistId": "mbid-sam-cooke",
        "id": 42,
    }])
    managed = client.get_managed_artist_by_mbid("mbid-sam-cooke")
    assert managed is not None
    assert managed["id"] == 42
    session.request.assert_called_once_with(
        "GET",
        "http://lidarr.test/api/v1/artist",
        params={"mbId": "mbid-sam-cooke"},
        timeout=20.0,
    )


def test_get_command_completed() -> None:
    client, _ = make_client({
        "id": 1234,
        "name": "AlbumSearch",
        "status": "completed",
    })
    status = client.get_command(1234)
    assert status.command_id == 1234
    assert status.completed is True
    assert status.successful is True


def test_get_command_failed() -> None:
    client, _ = make_client({
        "id": 1234,
        "name": "AlbumSearch",
        "status": "failed",
        "message": "Indexer unavailable",
    })
    status = client.get_command(1234)
    assert status.completed is True
    assert status.successful is False
    assert status.message == "Indexer unavailable"


@patch("plex_playlist.lidarr_client.sleep")
def test_wait_for_command_polls_until_complete(mock_sleep) -> None:
    client = Mock(spec=LidarrClient)
    client.get_command.side_effect = [
        LidarrClient._parse_command_status(
            {"id": 1, "status": "started"}, 1
        ),
        LidarrClient._parse_command_status(
            {"id": 1, "status": "completed"}, 1
        ),
    ]
    result = LidarrClient.wait_for_command(
        client,
        1,
        timeout_seconds=10,
        poll_interval_seconds=0.01,
    )
    assert result.successful is True
    assert client.get_command.call_count == 2
    mock_sleep.assert_called_once_with(0.01)

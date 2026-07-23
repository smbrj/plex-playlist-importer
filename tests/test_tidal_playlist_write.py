from plex_playlist.tidal_account import TidalAccountClient


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.text = ""
    def json(self):
        return self.payload


class WriteSession:
    def __init__(self):
        self.post_calls = []
        self.get_calls = []
        self.delete_calls = []
    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse(201, {
            "data": {
                "type": "playlists",
                "id": "playlist-1",
                "attributes": {"name": "PPI WRITE TEST"},
            }
        })
    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse(200, {
            "data": {
                "type": "playlists",
                "id": "playlist-1",
                "attributes": {"name": "PPI WRITE TEST"},
            }
        })
    def delete(self, url, **kwargs):
        self.delete_calls.append((url, kwargs))
        return FakeResponse(204, {})


def test_create_verify_delete_playlist_request_shapes():
    session = WriteSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    created = client.create_playlist(
        "PPI WRITE TEST",
        description="Temporary",
        access_type="UNLISTED",
    )
    assert created.playlist_id == "playlist-1"

    url, kwargs = session.post_calls[0]
    assert url == "https://openapi.tidal.com/v2/playlists"
    assert kwargs["params"] == {"countryCode": "US"}
    assert kwargs["headers"]["Content-Type"] == "application/vnd.api+json"
    assert kwargs["headers"]["Idempotency-Key"]
    assert kwargs["json"] == {
        "data": {
            "type": "playlists",
            "attributes": {
                "name": "PPI WRITE TEST",
                "description": "Temporary",
                "accessType": "UNLISTED",
            },
        }
    }

    verified = client.get_playlist(created.playlist_id)
    assert verified.name == "PPI WRITE TEST"

    client.delete_playlist(created.playlist_id)
    delete_url, delete_kwargs = session.delete_calls[0]
    assert delete_url == "https://openapi.tidal.com/v2/playlists/playlist-1"
    assert delete_kwargs["headers"]["Idempotency-Key"]


def test_create_playlist_rejects_blank_name():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=WriteSession(),
    )
    try:
        client.create_playlist("   ")
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:
        raise AssertionError("blank playlist name was accepted")

from plex_playlist.tidal_account import TidalAccountClient


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.headers = {}
        self.text = ""

    def json(self):
        return self.payload


class PlaylistItemSession:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse(
            200,
            {
                "data": [
                    {
                        "type": "tracks",
                        "id": "1",
                        "meta": {"itemId": "occ-1"},
                    },
                    {
                        "type": "videos",
                        "id": "v1",
                        "meta": {"itemId": "occ-v1"},
                    },
                    {
                        "type": "tracks",
                        "id": "2",
                        "meta": {"itemId": "occ-2"},
                    },
                ],
                "links": {},
            },
        )

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse(
            200,
            {
                "data": kwargs["json"]["data"],
                "links": {},
            },
        )


def test_playlist_track_ids_ignore_video_items():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=PlaylistItemSession(),
    )

    assert client.list_playlist_track_ids("p1") == {"1", "2"}


def test_add_playlist_tracks_deduplicates_and_uses_jsonapi():
    session = PlaylistItemSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    client.add_playlist_tracks("p1", ["10", "10", "20"])

    url, kwargs = session.post_calls[0]
    assert url == (
        "https://openapi.tidal.com/v2/"
        "playlists/p1/relationships/items"
    )
    assert kwargs["params"] == {"countryCode": "US"}
    assert kwargs["headers"]["Content-Type"] == "application/vnd.api+json"
    assert kwargs["headers"]["Idempotency-Key"]
    assert kwargs["json"] == {
        "data": [
            {"type": "tracks", "id": "10"},
            {"type": "tracks", "id": "20"},
        ]
    }


def test_playlist_relationship_items_preserve_server_meta():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=PlaylistItemSession(),
    )

    items = client.list_playlist_relationship_items("p1")

    assert items[0].item_type == "tracks"
    assert items[0].item_id == "1"
    assert items[0].meta == {"itemId": "occ-1"}

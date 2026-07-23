from plex_playlist.tidal_account import TidalAccountClient


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class PagingSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))

        if url == "https://openapi.tidal.com/v2/playlists":
            return FakeResponse({
                "data": [
                    {
                        "type": "playlists",
                        "id": "p1",
                        "attributes": {"name": "First"},
                    }
                ],
                "links": {
                    "next": "/playlists?filter%5Bowners.id%5D=me&page%5Bcursor%5D=abc"
                },
            })

        if url == (
            "https://openapi.tidal.com/v2/"
            "playlists?filter%5Bowners.id%5D=me&page%5Bcursor%5D=abc"
        ):
            return FakeResponse({
                "data": [
                    {
                        "type": "playlists",
                        "id": "p2",
                        "attributes": {"name": "Second"},
                    }
                ],
                "links": {},
            })

        if url.endswith("/userCollectionTracks/me/relationships/items"):
            return FakeResponse({
                "data": [{"type": "tracks", "id": "1"}],
                "links": {
                    "next": "/userCollectionTracks/me/relationships/items?page%5Bcursor%5D=xyz"
                },
            })

        if url == (
            "https://openapi.tidal.com/v2/"
            "userCollectionTracks/me/relationships/items?page%5Bcursor%5D=xyz"
        ):
            return FakeResponse({
                "data": [{"type": "tracks", "id": "2"}],
                "links": {},
            })

        raise AssertionError(f"Unexpected URL: {url}")


def test_playlist_pagination_resolves_relative_next_link():
    session = PagingSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    playlists = client.list_owned_playlists()

    assert [p.name for p in playlists] == ["First", "Second"]


def test_favorite_pagination_resolves_relative_next_link():
    session = PagingSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    count = client.count_favorite_tracks()

    assert count == 2


def test_absolute_next_link_is_preserved():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=PagingSession(),
    )

    absolute = "https://example.test/v2/items?page=2"
    assert client._resolve_next_url(absolute) == absolute


def test_relative_next_link_preserves_v2_base_path():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=PagingSession(),
    )
    assert client._resolve_next_url("/playlists?page=2") == (
        "https://openapi.tidal.com/v2/playlists?page=2"
    )

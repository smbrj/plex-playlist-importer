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


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))

        if "/playlists" in url:
            return FakeResponse({
                "data": [
                    {
                        "type": "playlists",
                        "id": "p1",
                        "attributes": {"name": "Road Trip"},
                    },
                    {
                        "type": "playlists",
                        "id": "p2",
                        "attributes": {"name": "test-tidal"},
                    },
                ],
                "links": {},
            })

        if "/userCollectionTracks/me/relationships/items" in url:
            return FakeResponse({
                "data": [
                    {"type": "tracks", "id": "1"},
                    {"type": "tracks", "id": "2"},
                    {"type": "tracks", "id": "3"},
                ],
                "links": {},
            })

        raise AssertionError(url)


def test_account_summary_is_read_only_and_counts_resources():
    session = FakeSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    summary = client.summary()

    assert [p.name for p in summary.playlists] == [
        "Road Trip",
        "test-tidal",
    ]
    assert summary.favorite_track_count == 3
    assert session.calls[0][1]["params"]["filter[owners.id]"] == "me"

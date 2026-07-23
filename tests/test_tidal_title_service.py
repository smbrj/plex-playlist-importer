from plex_playlist.tidal_service import TidalSearchService


class FakeClient:
    def __init__(self):
        self.calls = []

    def search_tracks(self, artist, title):
        self.calls.append((artist, title))
        return []


def test_service_searches_cleaned_title():
    client = FakeClient()
    service = TidalSearchService(client=client)

    service.resolve("Sublime", "What I Got (96)")

    assert client.calls == [("Sublime", "What I Got")]

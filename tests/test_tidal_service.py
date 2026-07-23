from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_service import TidalSearchService


class FakeClient:
    def __init__(self, results):
        self.results = results
        self.calls = 0

    def search_tracks(self, artist, title):
        self.calls += 1
        return list(self.results)


def candidate():
    return TidalTrackCandidate(
        track_id="317688870",
        artist="Steely Dan",
        title="Peg",
        album="Aja",
        quality="HIRES_LOSSLESS,LOSSLESS",
    )


def test_match_is_cached_and_second_resolution_avoids_api(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = FakeClient([candidate()])
    service = TidalSearchService(client=client, cache=cache)

    first = service.resolve("Steely Dan", "Peg")
    second = service.resolve("Steely Dan", "Peg")

    assert first.source == "api"
    assert second.source == "cache"
    assert second.matched.track_id == "317688870"
    assert client.calls == 1


def test_no_match_is_negative_cached(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = FakeClient([])
    service = TidalSearchService(client=client, cache=cache)

    first = service.resolve("Missing", "Track")
    second = service.resolve("Missing", "Track")

    assert first.matched is None
    assert second.matched is None
    assert second.source == "cache"
    assert client.calls == 1

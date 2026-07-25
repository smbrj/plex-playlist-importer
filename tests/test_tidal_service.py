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


def test_api_resolution_preserves_search_title_and_candidates(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    result_candidate = candidate()
    client = FakeClient([result_candidate])
    service = TidalSearchService(client=client, cache=cache)

    resolution = service.resolve("Steely Dan", "Peg (1977)")

    assert resolution.source == "api"
    assert resolution.search_title == "Peg"
    assert resolution.candidates == (result_candidate,)


def test_cached_no_match_has_no_candidate_diagnostics(tmp_path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = FakeClient([])
    service = TidalSearchService(client=client, cache=cache)

    service.resolve("Missing", "Track")
    cached = service.resolve("Missing", "Track")

    assert cached.source == "cache"
    assert cached.search_title == "Track"
    assert cached.candidates == ()


def test_hydration_failure_makes_no_match_inconclusive_and_not_cached(tmp_path):
    from plex_playlist.tidal_client import TidalHydrationFailure

    class HydrationFailingClient:
        def __init__(self):
            self.calls = 0
            self.last_hydration_failures = ()

        def search_tracks(self, artist, title):
            self.calls += 1
            sparse = TidalTrackCandidate(
                track_id="540307",
                artist="",
                title="Bark at the Moon",
                album="",
                quality="HIRES_LOSSLESS,LOSSLESS",
            )
            self.last_hydration_failures = (
                TidalHydrationFailure(
                    track_id="540307",
                    error="TIDAL track detail failed with HTTP 503",
                ),
            )
            return [sparse]

    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = HydrationFailingClient()
    service = TidalSearchService(client=client, cache=cache)

    first = service.resolve("Ozzy Osbourne", "Bark At The Moon")
    second = service.resolve("Ozzy Osbourne", "Bark At The Moon")

    assert first.matched is None
    assert first.source == "api"
    assert first.inconclusive is True
    assert first.hydration_failures[0].track_id == "540307"
    assert second.source == "api"
    assert client.calls == 2

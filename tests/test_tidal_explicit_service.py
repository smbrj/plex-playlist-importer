from pathlib import Path

from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_service import TidalSearchService


class FakeClient:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.calls = 0

    def search_tracks(self, artist, title):
        self.calls += 1
        return list(self.candidates)


def explicit_candidate():
    return TidalTrackCandidate(
        track_id="explicit",
        artist="Test Artist",
        title="Test Song",
        album="Album",
        quality="DOLBY_ATMOS",
        explicit=True,
    )


def test_service_negative_cache_under_false_does_not_mask_true_policy(
    tmp_path: Path,
):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = FakeClient([explicit_candidate()])

    blocked = TidalSearchService(
        client=client,
        cache=cache,
        allow_explicit=False,
    ).resolve("Test Artist", "Test Song")
    allowed = TidalSearchService(
        client=client,
        cache=cache,
        allow_explicit=True,
    ).resolve("Test Artist", "Test Song")

    assert blocked.matched is None
    assert blocked.source == "api"
    assert allowed.matched is not None
    assert allowed.matched.track_id == "explicit"
    assert allowed.source == "api"
    assert client.calls == 2


def test_service_reuses_explicit_policy_specific_cache(tmp_path: Path):
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    client = FakeClient([explicit_candidate()])
    service = TidalSearchService(
        client=client,
        cache=cache,
        allow_explicit=True,
    )

    first = service.resolve("Test Artist", "Test Song")
    second = service.resolve("Test Artist", "Test Song")

    assert first.source == "api"
    assert second.source == "cache"
    assert second.matched is not None
    assert second.matched.explicit is True
    assert client.calls == 1

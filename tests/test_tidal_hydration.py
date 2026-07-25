from plex_playlist.tidal_client import TidalClient
from plex_playlist.tidal_matcher import qualifying_candidates


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        return FakeResponse({"access_token": "token", "expires_in": 3600})

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))

        if "/searchResults/" in url:
            return FakeResponse({
                "data": {"type": "searchResults", "id": "q"},
                "included": [
                    {
                        "type": "tracks",
                        "id": "1",
                        "attributes": {"title": "Peg"},
                    },
                    {
                        "type": "tracks",
                        "id": "2",
                        "attributes": {"title": "Black Cow"},
                    },
                ],
            })

        if url.endswith("/tracks/1"):
            return FakeResponse({
                "data": {
                    "type": "tracks",
                    "id": "1",
                    "attributes": {
                        "title": "Peg",
                        "version": "",
                        "mediaTags": ["HIRES_LOSSLESS"],
                    },
                    "relationships": {
                        "artists": {
                            "data": [{"type": "artists", "id": "a1"}]
                        },
                        "albums": {
                            "data": [{"type": "albums", "id": "al1"}]
                        },
                    },
                },
                "included": [
                    {
                        "type": "artists",
                        "id": "a1",
                        "attributes": {"name": "Steely Dan"},
                    },
                    {
                        "type": "albums",
                        "id": "al1",
                        "attributes": {"title": "Aja"},
                    },
                ],
            })

        raise AssertionError(f"Unexpected URL {url}")


def test_search_hydrates_only_title_matching_candidates():
    session = FakeSession()
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    results = client.search_tracks("Steely Dan", "Peg")

    assert len(results) == 2

    peg = results[0]
    assert peg.artist == "Steely Dan"
    assert peg.album == "Aja"
    assert peg.quality == "HIRES_LOSSLESS"

    black_cow = results[1]
    assert black_cow.artist == ""

    detail_calls = [
        url for url, _ in session.calls if "/tracks/" in url
    ]
    assert detail_calls == [
        "https://openapi.tidal.com/v2/tracks/1"
    ]


def test_separate_live_version_is_rejected():
    from plex_playlist.tidal_client import TidalTrackCandidate

    candidate = TidalTrackCandidate(
        track_id="1",
        artist="Steely Dan",
        title="Peg",
        album="Aja",
        quality="LOSSLESS",
        version="Live",
    )

    accepted = qualifying_candidates(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[candidate],
    )

    assert accepted == []


def test_separate_remaster_version_is_accepted():
    from plex_playlist.tidal_client import TidalTrackCandidate

    candidate = TidalTrackCandidate(
        track_id="1",
        artist="Steely Dan",
        title="Peg",
        album="Aja",
        quality="HIRES_LOSSLESS",
        version="2011 Remaster",
    )

    accepted = qualifying_candidates(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[candidate],
    )

    assert accepted == [candidate]


def test_hydration_failure_is_recorded_and_sparse_candidate_preserved():
    class FailingHydrationSession(FakeSession):
        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if "/searchResults/" in url:
                return FakeResponse({
                    "data": {"type": "searchResults", "id": "q"},
                    "included": [
                        {
                            "type": "tracks",
                            "id": "540307",
                            "attributes": {
                                "title": "Bark at the Moon",
                                "mediaTags": ["HIRES_LOSSLESS", "LOSSLESS"],
                            },
                        }
                    ],
                })
            if url.endswith("/tracks/540307"):
                return FakeResponse({}, status_code=503)
            raise AssertionError(f"Unexpected URL {url}")

    session = FailingHydrationSession()
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    results = client.search_tracks("Ozzy Osbourne", "Bark At The Moon")

    assert len(results) == 1
    assert results[0].track_id == "540307"
    assert results[0].artist == ""
    assert len(client.last_hydration_failures) == 1
    failure = client.last_hydration_failures[0]
    assert failure.track_id == "540307"
    assert "HTTP 503" in failure.error


def test_hydration_calls_are_paced_between_matching_candidates(monkeypatch):
    class TwoMatchingSession(FakeSession):
        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if "/searchResults/" in url:
                return FakeResponse({
                    "data": {"type": "searchResults", "id": "q"},
                    "included": [
                        {"type": "tracks", "id": "1", "attributes": {"title": "Peg"}},
                        {"type": "tracks", "id": "2", "attributes": {"title": "Peg"}},
                    ],
                })
            if url.endswith("/tracks/1") or url.endswith("/tracks/2"):
                track_id = url.rsplit("/", 1)[-1]
                return FakeResponse({
                    "data": {
                        "type": "tracks",
                        "id": track_id,
                        "attributes": {"title": "Peg", "version": "", "mediaTags": ["LOSSLESS"]},
                        "relationships": {
                            "artists": {"data": [{"type": "artists", "id": "a1"}]},
                            "albums": {"data": [{"type": "albums", "id": "al1"}]},
                        },
                    },
                    "included": [
                        {"type": "artists", "id": "a1", "attributes": {"name": "Steely Dan"}},
                        {"type": "albums", "id": "al1", "attributes": {"title": "Aja"}},
                    ],
                })
            raise AssertionError(f"Unexpected URL {url}")

    sleeps = []
    monkeypatch.setattr("plex_playlist.tidal_client.time.sleep", sleeps.append)

    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=TwoMatchingSession(),
        hydration_delay_seconds=0.25,
    )
    client.search_tracks("Steely Dan", "Peg")

    assert sleeps == [0.25]


def test_hydration_delay_can_be_disabled(monkeypatch):
    sleeps = []
    monkeypatch.setattr("plex_playlist.tidal_client.time.sleep", sleeps.append)

    session = FakeSession()
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
        hydration_delay_seconds=0,
    )
    client.search_tracks("Steely Dan", "Peg")

    assert sleeps == []


def test_negative_hydration_delay_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="cannot be negative"):
        TidalClient(
            client_id="client",
            client_secret="secret",
            hydration_delay_seconds=-0.1,
        )

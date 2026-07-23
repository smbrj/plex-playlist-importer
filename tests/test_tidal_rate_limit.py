from plex_playlist.tidal_account import TidalAccountClient


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self.payload


class RateLimitedSession:
    def __init__(self):
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return FakeResponse(
                429,
                {"detail": "rate limited"},
                {"Retry-After": "1"},
            )
        return FakeResponse(200, {"data": [], "links": {}})


def test_get_retries_429_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(
        "plex_playlist.tidal_account.time.sleep",
        lambda value: sleeps.append(value),
    )
    session = RateLimitedSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
        rate_limit_retries=2,
    )
    assert client.list_favorite_track_ids() == set()
    assert session.calls == 2
    assert sleeps == [1.0]


def test_retry_after_fallback_is_exponential():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        rate_limit_fallback_seconds=5,
    )
    response = FakeResponse(429, headers={})
    assert client._retry_after_seconds(response, 0) == 5
    assert client._retry_after_seconds(response, 1) == 10
    assert client._retry_after_seconds(response, 2) == 20

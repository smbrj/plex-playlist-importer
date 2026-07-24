from pathlib import Path
import json
import time

from plex_playlist.tidal_user_auth import (
    TidalTokenStore,
    TidalUserTokenProvider,
    TidalUserTokens,
    refresh_user_tokens,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.post_calls = []

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse(200, self.payload)


def test_refresh_request_includes_client_id():
    session = FakeSession(
        {
            "access_token": "new-access",
            "refresh_token": "rotated-refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "user.read playlists.read",
        }
    )

    refresh_user_tokens(
        client_id="ppi-client",
        refresh_token="old-refresh",
        session=session,
    )

    assert len(session.post_calls) == 1
    _, kwargs = session.post_calls[0]
    assert kwargs["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": "old-refresh",
        "client_id": "ppi-client",
    }


def test_refresh_preserves_old_refresh_token_when_response_omits_one():
    session = FakeSession(
        {
            "access_token": "new-access",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "user.read",
        }
    )

    tokens = refresh_user_tokens(
        client_id="ppi-client",
        refresh_token="old-refresh",
        session=session,
    )

    assert tokens.refresh_token == "old-refresh"


def test_provider_uses_configured_client_id_when_refreshing(tmp_path: Path):
    store = TidalTokenStore(tmp_path / "tokens.json")
    store.save(
        TidalUserTokens(
            access_token="expired-access",
            refresh_token="old-refresh",
            expires_at=time.time() - 60,
            scope="user.read",
            token_type="Bearer",
        )
    )

    session = FakeSession(
        {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "user.read",
        }
    )

    provider = TidalUserTokenProvider(
        client_id="ppi-client",
        store=store,
        session=session,
    )

    assert provider.access_token() == "new-access"
    _, kwargs = session.post_calls[0]
    assert kwargs["data"]["client_id"] == "ppi-client"
    assert store.load().refresh_token == "new-refresh"

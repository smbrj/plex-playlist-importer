import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from plex_playlist.tidal_user_auth import (
    READ_SCOPES,
    TidalTokenStore,
    TidalUserTokens,
    build_authorization_url,
)


def test_authorization_url_requests_read_scopes_and_pkce():
    url = build_authorization_url(
        client_id="client",
        redirect_uri="http://127.0.0.1:8765/callback",
        state="state123",
        code_challenge="challenge123",
    )
    query = parse_qs(urlparse(url).query)

    assert query["scope"] == [" ".join(READ_SCOPES)]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["state123"]


def test_read_scopes_have_no_write_permission():
    assert READ_SCOPES == (
        "playlists.read",
        "collection.read",
        "user.read",
    )
    assert all("write" not in scope for scope in READ_SCOPES)


def test_token_store_round_trip(tmp_path: Path):
    store = TidalTokenStore(tmp_path / "tidal_tokens.json")
    tokens = TidalUserTokens(
        access_token="access",
        refresh_token="refresh",
        expires_at=9999999999,
        scope="playlists.read collection.read user.read",
    )

    store.save(tokens)
    assert store.load() == tokens

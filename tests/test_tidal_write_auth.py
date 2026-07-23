from urllib.parse import parse_qs, urlparse

from plex_playlist.tidal_user_auth import WRITE_SCOPES, build_authorization_url


def test_write_scopes_include_required_read_and_write_permissions():
    assert WRITE_SCOPES == (
        "playlists.read",
        "playlists.write",
        "collection.read",
        "collection.write",
        "user.read",
    )


def test_write_authorization_url_contains_write_scopes():
    url = build_authorization_url(
        client_id="client",
        redirect_uri="http://127.0.0.1:8765/callback",
        scopes=WRITE_SCOPES,
        state="state",
        code_challenge="challenge",
    )
    query = parse_qs(urlparse(url).query)
    assert query["scope"] == [" ".join(WRITE_SCOPES)]

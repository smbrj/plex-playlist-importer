import pytest
from plex_playlist.tidal_account import TidalAccountClient, TidalAccountError

class StaticProvider:
    def access_token(self):
        return "user-token"

class ErrorResponse:
    status_code = 404
    text = ""
    def json(self):
        return {"detail": "Not Found"}

class ErrorSession:
    def get(self, url, **kwargs):
        return ErrorResponse()

def test_account_error_includes_url_and_detail():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=ErrorSession(),
    )
    with pytest.raises(TidalAccountError) as exc:
        client._get_json("https://openapi.tidal.com/v2/playlists?page=2")
    message = str(exc.value)
    assert "HTTP 404" in message
    assert "https://openapi.tidal.com/v2/playlists?page=2" in message
    assert "Not Found" in message

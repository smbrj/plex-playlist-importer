from plex_playlist.tidal_client import TidalClient


class FakeResponse:
    status_code = 200

    def json(self):
        return {"data": {}, "included": []}


class FakeSession:
    def __init__(self):
        self.get_kwargs = None

    def post(self, url, **kwargs):
        class AuthResponse:
            status_code = 200
            def json(self):
                return {"access_token": "token", "expires_in": 3600}
        return AuthResponse()

    def get(self, url, **kwargs):
        self.get_kwargs = kwargs
        return FakeResponse()


def test_search_uses_current_tidal_jsonapi_request_shape():
    session = FakeSession()
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    client.search_tracks("Steely Dan", "Peg")

    assert session.get_kwargs["params"] == {
        "countryCode": "US",
        "include": "tracks,artists,albums",
    }
    assert (
        session.get_kwargs["headers"]["Accept"]
        == "application/vnd.api+json"
    )

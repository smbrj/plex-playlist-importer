from plex_playlist.tidal_account import TidalAccountClient


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.text = ""

    def json(self):
        return self.payload


class FavoriteSession:
    def __init__(self):
        self.favorite = False
        self.get_calls = []
        self.post_calls = []
        self.delete_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        data = (
            [{"type": "tracks", "id": "317688870"}]
            if self.favorite
            else []
        )
        return FakeResponse(
            200,
            {
                "data": data,
                "links": {},
            },
        )

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        self.favorite = True
        return FakeResponse(
            200,
            {
                "data": [{"type": "tracks", "id": "317688870"}],
                "links": {},
                "meta": {"skipped": []},
            },
        )

    def delete(self, url, **kwargs):
        self.delete_calls.append((url, kwargs))
        self.favorite = False
        return FakeResponse(204, {})


def test_favorite_add_verify_remove_request_shapes():
    session = FavoriteSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    assert client.is_favorite_track("317688870") is False

    client.add_favorite_track("317688870")
    assert client.is_favorite_track("317688870") is True

    url, kwargs = session.post_calls[0]
    assert url == (
        "https://openapi.tidal.com/v2/"
        "userCollectionTracks/me/relationships/items"
    )
    assert kwargs["headers"]["Content-Type"] == "application/vnd.api+json"
    assert kwargs["headers"]["Idempotency-Key"]
    assert kwargs["json"] == {
        "data": [{"type": "tracks", "id": "317688870"}]
    }

    client.remove_favorite_track("317688870")
    assert client.is_favorite_track("317688870") is False

    delete_url, delete_kwargs = session.delete_calls[0]
    assert delete_url == url
    assert delete_kwargs["headers"]["Content-Type"] == "application/vnd.api+json"
    assert delete_kwargs["headers"]["Idempotency-Key"]
    assert delete_kwargs["json"] == {
        "data": [{"type": "tracks", "id": "317688870"}]
    }


def test_list_favorite_track_ids_follows_pagination():
    class PagingSession:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return FakeResponse(
                    200,
                    {
                        "data": [{"type": "tracks", "id": "1"}],
                        "links": {
                            "next": (
                                "/userCollectionTracks/me/relationships/items"
                                "?page%5Bcursor%5D=abc"
                            )
                        },
                    },
                )
            return FakeResponse(
                200,
                {
                    "data": [{"type": "tracks", "id": "2"}],
                    "links": {},
                },
            )

    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=PagingSession(),
    )
    assert client.list_favorite_track_ids() == {"1", "2"}


def test_favorite_methods_reject_blank_track_id():
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=FavoriteSession(),
    )

    for method in (
        client.is_favorite_track,
        client.add_favorite_track,
        client.remove_favorite_track,
    ):
        try:
            method(" ")
        except ValueError as exc:
            assert "must not be empty" in str(exc)
        else:
            raise AssertionError("blank track id was accepted")

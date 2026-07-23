import pytest

from plex_playlist.tidal_account import (
    TidalAccountClient,
    TidalAccountError,
)


class StaticProvider:
    def access_token(self):
        return "user-token"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.headers = {}
        self.text = ""

    def json(self):
        return self.payload


class DeleteSession:
    def __init__(self, relationship_data=None):
        self.delete_calls = []
        self.get_calls = []
        self.relationship_data = relationship_data or [
            {
                "type": "tracks",
                "id": "10",
                "meta": {"itemId": "occ-10"},
            },
            {
                "type": "tracks",
                "id": "20",
                "meta": {"itemId": "occ-20"},
            },
        ]

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return FakeResponse(
            200,
            {
                "data": self.relationship_data,
                "links": {},
            },
        )

    def delete(self, url, **kwargs):
        self.delete_calls.append((url, kwargs))
        return FakeResponse(204)


def test_remove_playlist_tracks_reuses_server_relationship_meta():
    session = DeleteSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    client.remove_playlist_tracks("p1", ["10", "10", "20"])

    assert len(session.get_calls) == 1
    url, kwargs = session.delete_calls[0]
    assert url == (
        "https://openapi.tidal.com/v2/"
        "playlists/p1/relationships/items"
    )
    assert kwargs["headers"]["Content-Type"] == "application/vnd.api+json"
    assert kwargs["headers"]["Idempotency-Key"]
    assert kwargs["json"] == {
        "data": [
            {
                "type": "tracks",
                "id": "10",
                "meta": {"itemId": "occ-10"},
            },
            {
                "type": "tracks",
                "id": "20",
                "meta": {"itemId": "occ-20"},
            },
        ]
    }


def test_remove_playlist_tracks_blank_list_is_noop():
    session = DeleteSession()
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    client.remove_playlist_tracks("p1", [])
    assert session.get_calls == []
    assert session.delete_calls == []


def test_remove_playlist_tracks_refuses_missing_server_meta():
    session = DeleteSession(
        relationship_data=[
            {"type": "tracks", "id": "10"},
        ]
    )
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    with pytest.raises(TidalAccountError) as exc:
        client.remove_playlist_tracks("p1", ["10"])

    assert "missing required meta" in str(exc.value)
    assert session.delete_calls == []


def test_remove_playlist_tracks_refuses_absent_requested_track():
    session = DeleteSession(
        relationship_data=[
            {
                "type": "tracks",
                "id": "20",
                "meta": {"itemId": "occ-20"},
            },
        ]
    )
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    with pytest.raises(TidalAccountError) as exc:
        client.remove_playlist_tracks("p1", ["10"])

    assert "were not present" in str(exc.value)
    assert session.delete_calls == []


def test_duplicate_track_occurrences_preserve_each_server_meta():
    session = DeleteSession(
        relationship_data=[
            {
                "type": "tracks",
                "id": "10",
                "meta": {"itemId": "occ-10-a"},
            },
            {
                "type": "tracks",
                "id": "10",
                "meta": {"itemId": "occ-10-b"},
            },
        ]
    )
    client = TidalAccountClient(
        token_provider=StaticProvider(),
        session=session,
    )

    client.remove_playlist_tracks("p1", ["10"])

    payload = session.delete_calls[0][1]["json"]["data"]
    assert payload == [
        {
            "type": "tracks",
            "id": "10",
            "meta": {"itemId": "occ-10-a"},
        },
        {
            "type": "tracks",
            "id": "10",
            "meta": {"itemId": "occ-10-b"},
        },
    ]

from __future__ import annotations

from dataclasses import dataclass

import pytest

from plex_playlist.tidal_client import (
    TidalAuthenticationError,
    TidalClient,
    TidalRequestError,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, *, auth_response=None, search_response=None):
        self.auth_response = auth_response or FakeResponse(
            200,
            {"access_token": "token-1", "expires_in": 3600},
        )
        self.search_response = search_response or FakeResponse(200, {})
        self.post_calls = []
        self.get_calls = []

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self.auth_response

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.search_response


def search_payload():
    return {
        "data": {
            "type": "searchResults",
            "id": "Steely Dan Peg",
            "relationships": {
                "tracks": {
                    "data": [{"type": "tracks", "id": "123"}]
                }
            },
        },
        "included": [
            {
                "type": "tracks",
                "id": "123",
                "attributes": {
                    "title": "Peg",
                    "audioQuality": "HI_RES_LOSSLESS",
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
    }


def test_client_credentials_auth_and_search():
    session = FakeSession(
        search_response=FakeResponse(200, search_payload())
    )
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    results = client.search_tracks("Steely Dan", "Peg")

    assert len(results) == 1
    assert results[0].track_id == "123"
    assert results[0].artist == "Steely Dan"
    assert results[0].title == "Peg"
    assert results[0].album == "Aja"
    assert results[0].quality == "HI_RES_LOSSLESS"

    assert len(session.post_calls) == 1
    assert len(session.get_calls) == 1
    _, get_kwargs = session.get_calls[0]
    assert get_kwargs["params"]["countryCode"] == "US"
    assert get_kwargs["params"]["include"] == "tracks,artists,albums"
    assert get_kwargs["headers"]["Accept"] == "application/vnd.api+json"


def test_access_token_is_reused():
    session = FakeSession(
        search_response=FakeResponse(200, search_payload())
    )
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    client.search_tracks("Steely Dan", "Peg")
    client.search_tracks("Steely Dan", "Peg")

    assert len(session.post_calls) == 1
    assert len(session.get_calls) == 2


def test_auth_failure_is_clear():
    session = FakeSession(
        auth_response=FakeResponse(401, {"error": "invalid_client"})
    )
    client = TidalClient(
        client_id="bad",
        client_secret="bad",
        session=session,
    )

    with pytest.raises(TidalAuthenticationError):
        client.search_tracks("Artist", "Title")


def test_search_failure_is_clear():
    session = FakeSession(
        search_response=FakeResponse(429, {"error": "rate_limited"})
    )
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    with pytest.raises(TidalRequestError):
        client.search_tracks("Artist", "Title")


def test_empty_query_does_not_authenticate():
    session = FakeSession()
    client = TidalClient(
        client_id="client",
        client_secret="secret",
        session=session,
    )

    assert client.search_tracks("", "") == []
    assert session.post_calls == []
    assert session.get_calls == []

from types import SimpleNamespace

import pytest
from plexapi.exceptions import NotFound

from plex_playlist.plex_client import PlexClient


class FakeLibrary:
    def fetchItem(self, rating_key):
        if rating_key == 2:
            raise NotFound("missing")
        return SimpleNamespace(ratingKey=str(rating_key))


def result(rating_key, artist="Artist", title="Track"):
    return SimpleNamespace(
        matched=SimpleNamespace(
            rating_key=rating_key,
            artist=artist,
            title=title,
        )
    )


def test_resolve_matches_collects_stale_plex_items():
    client = PlexClient("http://plex", "token", "Music")
    client.server = object()
    client.library = FakeLibrary()

    resolution = client.resolve_matches([
        result(1),
        result(2, "Deleted Artist", "Deleted Track"),
        result(3),
        SimpleNamespace(matched=None),
    ])

    assert [int(item.ratingKey) for item in resolution.tracks] == [1, 3]
    assert len(resolution.stale_matches) == 1
    assert resolution.stale_matches[0].rating_key == 2
    assert resolution.stale_matches[0].artist == "Deleted Artist"


def test_resolve_matches_propagates_unexpected_errors():
    class BrokenLibrary:
        def fetchItem(self, rating_key):
            raise RuntimeError("connection failed")

    client = PlexClient("http://plex", "token", "Music")
    client.server = object()
    client.library = BrokenLibrary()

    with pytest.raises(RuntimeError, match="connection failed"):
        client.resolve_matches([result(1)])

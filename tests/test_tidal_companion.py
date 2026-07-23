import pytest

from plex_playlist.tidal_account import TidalAccountError, TidalUserPlaylist
from plex_playlist.tidal_companion import TidalCompanionPlaylistService


class FakeAccount:
    def __init__(
        self,
        playlists=None,
        existing=None,
        favorites=None,
    ):
        self.playlists = list(playlists or [])
        self.existing = set(existing or [])
        self.favorites = set(favorites or [])
        self.created = []
        self.added = []
        self.favorite_adds = []

    def list_owned_playlists(self):
        return list(self.playlists)

    def create_playlist(self, name, *, description="", access_type="UNLISTED"):
        playlist = TidalUserPlaylist("new-id", name)
        self.playlists.append(playlist)
        self.created.append((name, description, access_type))
        return playlist

    def list_playlist_track_ids(self, playlist_id):
        return set(self.existing)

    def add_playlist_tracks(self, playlist_id, track_ids):
        self.added.append((playlist_id, list(track_ids)))
        self.existing.update(track_ids)

    def list_favorite_track_ids(self):
        return set(self.favorites)

    def add_favorite_track(self, track_id):
        self.favorite_adds.append(track_id)
        self.favorites.add(track_id)


def test_creates_same_named_companion_and_adds_tracks():
    account = FakeAccount()
    service = TidalCompanionPlaylistService(account)

    result = service.add_missing_tracks(
        playlist_name="test-tidal",
        track_ids=["10", "20"],
    )

    assert result.playlist_created is True
    assert result.playlist.name == "test-tidal"
    assert result.added_track_ids == ("10", "20")
    assert result.favorite_added_track_ids == ("10", "20")
    assert result.favorite_existing_track_ids == ()
    assert account.created[0][2] == "UNLISTED"
    assert account.added == [("new-id", ["10", "20"])]
    assert account.favorite_adds == ["10", "20"]


def test_reuses_existing_playlist_and_skips_existing_tracks():
    account = FakeAccount(
        playlists=[TidalUserPlaylist("p1", "Test-Tidal")],
        existing={"10"},
        favorites={"20"},
    )
    service = TidalCompanionPlaylistService(account)

    result = service.add_missing_tracks(
        playlist_name="test-tidal",
        track_ids=["10", "20", "20"],
    )

    assert result.playlist_created is False
    assert result.existing_track_ids == ("10",)
    assert result.added_track_ids == ("20",)
    assert result.favorite_added_track_ids == ("10",)
    assert result.favorite_existing_track_ids == ("20",)
    assert account.created == []
    assert account.added == [("p1", ["20"])]
    assert account.favorite_adds == ["10"]


def test_duplicate_same_named_owned_playlists_are_ambiguous():
    account = FakeAccount(
        playlists=[
            TidalUserPlaylist("p1", "Mix"),
            TidalUserPlaylist("p2", "mix"),
        ]
    )
    service = TidalCompanionPlaylistService(account)

    with pytest.raises(TidalAccountError):
        service.add_missing_tracks(
            playlist_name="MIX",
            track_ids=["10"],
        )


def test_second_sync_is_fully_idempotent_for_playlist_and_favorites():
    account = FakeAccount(
        playlists=[TidalUserPlaylist("p1", "Mix")],
        existing={"10", "20"},
        favorites={"10", "20"},
    )
    service = TidalCompanionPlaylistService(account)

    result = service.add_missing_tracks(
        playlist_name="Mix",
        track_ids=["10", "20"],
    )

    assert result.added_track_ids == ()
    assert result.existing_track_ids == ("10", "20")
    assert result.favorite_added_track_ids == ()
    assert result.favorite_existing_track_ids == ("10", "20")
    assert account.added == []
    assert account.favorite_adds == []

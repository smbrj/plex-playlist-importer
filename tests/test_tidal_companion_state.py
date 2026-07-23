from pathlib import Path

from plex_playlist.tidal_account import TidalUserPlaylist
from plex_playlist.tidal_companion import TidalCompanionPlaylistService
from plex_playlist.tidal_state import TidalStateStore


class FakeAccount:
    def __init__(self, *, favorites=None):
        self.playlists = [TidalUserPlaylist("p1", "Mix")]
        self.playlist_tracks = set()
        self.favorites = set(favorites or [])

    def list_owned_playlists(self):
        return self.playlists

    def create_playlist(self, *args, **kwargs):
        raise AssertionError("playlist should already exist")

    def list_playlist_track_ids(self, playlist_id):
        return set(self.playlist_tracks)

    def add_playlist_tracks(self, playlist_id, track_ids):
        self.playlist_tracks.update(track_ids)

    def list_favorite_track_ids(self):
        return set(self.favorites)

    def add_favorite_track(self, track_id):
        self.favorites.add(track_id)


def test_sync_records_ppi_owned_favorite_and_membership(tmp_path: Path):
    state = TidalStateStore(tmp_path / "tidal_state.db")
    service = TidalCompanionPlaylistService(
        FakeAccount(),
        state_store=state,
    )

    service.add_missing_tracks(
        playlist_name="Mix",
        track_ids=["10"],
        metadata_by_track_id={
            "10": ("Artist", "Song", "Album"),
        },
    )

    track = state.get_track("10")
    assert track is not None
    assert track.favorite_added_by_ppi is True
    assert (track.artist, track.title, track.album) == (
        "Artist",
        "Song",
        "Album",
    )
    assert state.count_memberships_for_track("10") == 1


def test_preexisting_favorite_is_recorded_as_not_owned(tmp_path: Path):
    state = TidalStateStore(tmp_path / "tidal_state.db")
    service = TidalCompanionPlaylistService(
        FakeAccount(favorites={"10"}),
        state_store=state,
    )

    service.add_missing_tracks(
        playlist_name="Mix",
        track_ids=["10"],
    )

    track = state.get_track("10")
    assert track is not None
    assert track.favorite_added_by_ppi is False


def test_existing_ppi_ownership_is_not_erased_on_later_sync(tmp_path: Path):
    state = TidalStateStore(tmp_path / "tidal_state.db")
    state.record_track(
        track_id="10",
        favorite_added_by_ppi=True,
    )

    service = TidalCompanionPlaylistService(
        FakeAccount(favorites={"10"}),
        state_store=state,
    )
    service.add_missing_tracks(
        playlist_name="Mix",
        track_ids=["10"],
    )

    track = state.get_track("10")
    assert track is not None
    assert track.favorite_added_by_ppi is True

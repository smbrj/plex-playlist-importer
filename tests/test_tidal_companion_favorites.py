from plex_playlist.tidal_account import TidalUserPlaylist
from plex_playlist.tidal_companion import TidalCompanionPlaylistService


class Account:
    def __init__(self):
        self.playlists = [TidalUserPlaylist("p", "test-tidal")]
        self.playlist_tracks = {"71324988"}
        self.favorites = {"190299390"}
        self.playlist_adds = []
        self.favorite_adds = []

    def list_owned_playlists(self):
        return self.playlists

    def create_playlist(self, *args, **kwargs):
        raise AssertionError("playlist should be reused")

    def list_playlist_track_ids(self, playlist_id):
        return set(self.playlist_tracks)

    def add_playlist_tracks(self, playlist_id, track_ids):
        self.playlist_adds.extend(track_ids)
        self.playlist_tracks.update(track_ids)

    def list_favorite_track_ids(self):
        return set(self.favorites)

    def add_favorite_track(self, track_id):
        self.favorite_adds.append(track_id)
        self.favorites.add(track_id)


def test_playlist_and_favorite_state_are_independent():
    account = Account()
    service = TidalCompanionPlaylistService(account)

    result = service.add_missing_tracks(
        playlist_name="test-tidal",
        track_ids=["71324988", "190299390"],
    )

    assert result.added_track_ids == ("190299390",)
    assert result.existing_track_ids == ("71324988",)
    assert result.favorite_added_track_ids == ("71324988",)
    assert result.favorite_existing_track_ids == ("190299390",)

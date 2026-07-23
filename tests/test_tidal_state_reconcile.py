from pathlib import Path

from plex_playlist.tidal_state import TidalStateStore


def test_count_other_memberships_excludes_current_playlist(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    store.record_track(track_id="10")
    store.record_membership(
        playlist_name="Mix A",
        playlist_id="p1",
        track_id="10",
    )
    store.record_membership(
        playlist_name="Mix B",
        playlist_id="p2",
        track_id="10",
    )

    assert store.count_other_memberships_for_track(
        track_id="10",
        excluding_playlist_name="Mix A",
    ) == 1


def test_remove_membership_is_scoped_to_playlist(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    store.record_track(track_id="10")
    store.record_membership(
        playlist_name="Mix A",
        playlist_id="p1",
        track_id="10",
    )
    store.record_membership(
        playlist_name="Mix B",
        playlist_id="p2",
        track_id="10",
    )

    store.remove_membership(
        playlist_name="Mix A",
        track_id="10",
    )

    assert store.count_memberships_for_track("10") == 1
    rows = store.list_memberships_for_track("10")
    assert rows[0].playlist_name == "Mix B"

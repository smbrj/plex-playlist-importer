from pathlib import Path

from plex_playlist.tidal_state import TidalStateStore


def test_track_and_membership_round_trip(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")

    store.record_track(
        track_id="10",
        artist="Artist",
        title="Song",
        album="Album",
        favorite_added_by_ppi=True,
    )
    store.record_membership(
        playlist_name="Mix A",
        playlist_id="p1",
        track_id="10",
    )

    track = store.get_track("10")
    assert track is not None
    assert track.artist == "Artist"
    assert track.title == "Song"
    assert track.album == "Album"
    assert track.favorite_added_by_ppi is True

    memberships = store.list_memberships_for_track("10")
    assert len(memberships) == 1
    assert memberships[0].playlist_name == "Mix A"
    assert memberships[0].playlist_id == "p1"


def test_favorite_ownership_is_sticky_true(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")

    store.record_track(
        track_id="10",
        favorite_added_by_ppi=True,
    )
    store.record_track(
        track_id="10",
        favorite_added_by_ppi=False,
    )

    track = store.get_track("10")
    assert track is not None
    assert track.favorite_added_by_ppi is True


def test_preexisting_favorite_stays_not_owned(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")

    store.record_track(
        track_id="20",
        favorite_added_by_ppi=False,
    )

    track = store.get_track("20")
    assert track is not None
    assert track.favorite_added_by_ppi is False


def test_same_track_can_belong_to_multiple_companions(tmp_path: Path):
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

    assert store.count_memberships_for_track("10") == 2
    assert {
        row.playlist_name
        for row in store.list_memberships_for_track("10")
    } == {"Mix A", "Mix B"}


def test_membership_upsert_refreshes_playlist_id_without_duplication(
    tmp_path: Path,
):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    store.record_track(track_id="10")

    store.record_membership(
        playlist_name="Mix",
        playlist_id="old",
        track_id="10",
    )
    store.record_membership(
        playlist_name="Mix",
        playlist_id="new",
        track_id="10",
    )

    rows = store.list_memberships_for_playlist("mix")
    assert len(rows) == 1
    assert rows[0].playlist_id == "new"

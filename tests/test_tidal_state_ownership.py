from pathlib import Path

from plex_playlist.tidal_state import TidalStateStore


def test_set_favorite_ownership_updates_existing_track(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    store.record_track(
        track_id="10",
        favorite_added_by_ppi=False,
    )

    store.set_favorite_ownership(
        track_id="10",
        owned_by_ppi=True,
    )

    track = store.get_track("10")
    assert track is not None
    assert track.favorite_added_by_ppi is True


def test_set_favorite_ownership_rejects_unknown_track(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")

    try:
        store.set_favorite_ownership(
            track_id="999",
            owned_by_ppi=True,
        )
    except ValueError as exc:
        assert "not present" in str(exc)
    else:
        raise AssertionError("unknown track ownership update was accepted")

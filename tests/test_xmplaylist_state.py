from pathlib import Path

from plex_playlist.xmplaylist_state import (
    XMPlaylistBackfillState,
    XMPlaylistStateStore,
)


def test_state_and_tracks_round_trip(tmp_path: Path) -> None:
    store = XMPlaylistStateStore(tmp_path / "xm.db")
    store.initialize()

    store.upsert_track(
        station_number=14,
        artist_key="fleetwood mac",
        title_key="dreams",
        artist="Fleetwood Mac",
        title="Dreams",
        last_seen_timestamp="2026-07-15T11:00:00+00:00",
    )
    store.save_state(
        XMPlaylistBackfillState(
            station_number=14,
            station_name="The Bridge",
            station_deeplink="thebridge",
            history_hours=8,
            next_cursor="cursor-2",
            oldest_timestamp="2026-07-15T11:00:00+00:00",
            backfill_complete=False,
        )
    )

    assert store.load_tracks(14) == [("Fleetwood Mac", "Dreams")]
    state = store.load_state(14)
    assert state is not None
    assert state.next_cursor == "cursor-2"
    assert state.backfill_complete is False


def test_delete_before_removes_expired_tracks(tmp_path: Path) -> None:
    store = XMPlaylistStateStore(tmp_path / "xm.db")
    store.initialize()

    for title, timestamp in [
        ("Old", "2026-07-01T00:00:00+00:00"),
        ("New", "2026-07-14T00:00:00+00:00"),
    ]:
        store.upsert_track(
            station_number=14,
            artist_key="artist",
            title_key=title.lower(),
            artist="Artist",
            title=title,
            last_seen_timestamp=timestamp,
        )

    removed = store.delete_before(
        station_number=14,
        cutoff_timestamp="2026-07-08T00:00:00+00:00",
    )

    assert removed == 1
    assert store.load_tracks(14) == [("Artist", "New")]

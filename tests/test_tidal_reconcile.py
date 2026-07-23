from pathlib import Path

from plex_playlist.tidal_reconcile import (
    TidalReconcileAction,
    TidalReconciliationPlanner,
)
from plex_playlist.tidal_state import TidalStateStore


def _seed(
    store: TidalStateStore,
    *,
    track_id: str,
    playlist_name: str,
    playlist_id: str,
    owned: bool,
):
    store.record_track(
        track_id=track_id,
        favorite_added_by_ppi=owned,
    )
    store.record_membership(
        playlist_name=playlist_name,
        playlist_id=playlist_id,
        track_id=track_id,
    )


def test_required_track_is_keep(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=True,
    )

    decisions = TidalReconciliationPlanner(store).plan(
        playlist_name="Mix",
        desired_track_ids=["10"],
    )

    assert len(decisions) == 1
    assert decisions[0].action == TidalReconcileAction.KEEP


def test_stale_ppi_owned_track_can_remove_playlist_and_favorite(
    tmp_path: Path,
):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=True,
    )

    decision = TidalReconciliationPlanner(store).plan(
        playlist_name="Mix",
        desired_track_ids=[],
    )[0]

    assert decision.action == (
        TidalReconcileAction.REMOVE_FROM_PLAYLIST_AND_FAVORITES
    )
    assert decision.other_companion_count == 0


def test_stale_user_owned_favorite_keeps_favorite(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=False,
    )

    decision = TidalReconciliationPlanner(store).plan(
        playlist_name="Mix",
        desired_track_ids=[],
    )[0]

    assert decision.action == TidalReconcileAction.KEEP_FAVORITE_USER_OWNED
    assert decision.favorite_added_by_ppi is False


def test_stale_shared_track_keeps_favorite(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix A",
        playlist_id="p1",
        owned=True,
    )
    store.record_membership(
        playlist_name="Mix B",
        playlist_id="p2",
        track_id="10",
    )

    decision = TidalReconciliationPlanner(store).plan(
        playlist_name="Mix A",
        desired_track_ids=[],
    )[0]

    assert decision.action == (
        TidalReconcileAction.KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION
    )
    assert decision.other_companion_count == 1


def test_planner_does_not_mutate_state(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=True,
    )

    TidalReconciliationPlanner(store).plan(
        playlist_name="Mix",
        desired_track_ids=[],
    )

    assert store.count_memberships_for_track("10") == 1

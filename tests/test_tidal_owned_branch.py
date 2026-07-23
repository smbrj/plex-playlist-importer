from pathlib import Path

from plex_playlist.tidal_reconcile import (
    TidalReconcileAction,
    TidalReconciliationExecutor,
    TidalReconciliationPlanner,
)
from plex_playlist.tidal_state import TidalStateStore


class FakeClient:
    def __init__(self):
        self.playlist_removes = []
        self.favorite_removes = []

    def remove_playlist_tracks(self, playlist_id, track_ids):
        self.playlist_removes.append((playlist_id, list(track_ids)))

    def remove_favorite_track(self, track_id):
        self.favorite_removes.append(track_id)


def test_owned_stale_track_plans_and_executes_both_removals(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    store.record_track(
        track_id="71324988",
        artist="69 Boyz",
        title="Tootsee Roll",
        favorite_added_by_ppi=True,
    )
    store.record_membership(
        playlist_name="test-tidal",
        playlist_id="p1",
        track_id="71324988",
    )

    decisions = TidalReconciliationPlanner(store).plan(
        playlist_name="test-tidal",
        desired_track_ids=[],
    )

    assert len(decisions) == 1
    assert decisions[0].action == (
        TidalReconcileAction.REMOVE_FROM_PLAYLIST_AND_FAVORITES
    )

    client = FakeClient()
    result = TidalReconciliationExecutor(
        client=client,
        state_store=store,
    ).execute(decisions)

    assert client.playlist_removes == [("p1", ["71324988"])]
    assert client.favorite_removes == ["71324988"]
    assert result.playlist_tracks_removed == ("71324988",)
    assert result.favorites_removed == ("71324988",)
    assert result.favorites_preserved == ()
    assert store.count_memberships_for_track("71324988") == 0

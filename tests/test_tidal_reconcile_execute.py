from pathlib import Path

from plex_playlist.tidal_reconcile import (
    TidalReconcileAction,
    TidalReconcileDecision,
    TidalReconciliationExecutor,
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


def _decision(
    *,
    action: TidalReconcileAction,
    track_id="10",
    playlist_name="Mix",
    playlist_id="p1",
    owned=False,
    other=0,
):
    return TidalReconcileDecision(
        playlist_name=playlist_name,
        playlist_id=playlist_id,
        track_id=track_id,
        action=action,
        reason="test",
        favorite_added_by_ppi=owned,
        other_companion_count=other,
    )


def test_user_owned_favorite_removes_playlist_only(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=False,
    )
    client = FakeClient()

    result = TidalReconciliationExecutor(
        client=client,
        state_store=store,
    ).execute([
        _decision(
            action=TidalReconcileAction.KEEP_FAVORITE_USER_OWNED,
        )
    ])

    assert client.playlist_removes == [("p1", ["10"])]
    assert client.favorite_removes == []
    assert store.count_memberships_for_track("10") == 0
    assert result.favorites_preserved == ("10",)


def test_owned_unshared_favorite_removes_both(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=True,
    )
    client = FakeClient()

    result = TidalReconciliationExecutor(
        client=client,
        state_store=store,
    ).execute([
        _decision(
            action=(
                TidalReconcileAction
                .REMOVE_FROM_PLAYLIST_AND_FAVORITES
            ),
            owned=True,
        )
    ])

    assert client.playlist_removes == [("p1", ["10"])]
    assert client.favorite_removes == ["10"]
    assert result.favorites_removed == ("10",)


def test_shared_favorite_removes_current_playlist_only(tmp_path: Path):
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
    client = FakeClient()

    TidalReconciliationExecutor(
        client=client,
        state_store=store,
    ).execute([
        _decision(
            action=(
                TidalReconcileAction
                .KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION
            ),
            playlist_name="Mix A",
            playlist_id="p1",
            owned=True,
            other=1,
        )
    ])

    assert client.playlist_removes == [("p1", ["10"])]
    assert client.favorite_removes == []
    assert store.count_memberships_for_track("10") == 1


def test_keep_makes_no_changes(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=True,
    )
    client = FakeClient()

    TidalReconciliationExecutor(
        client=client,
        state_store=store,
    ).execute([
        _decision(
            action=TidalReconcileAction.KEEP,
            owned=True,
        )
    ])

    assert client.playlist_removes == []
    assert client.favorite_removes == []
    assert store.count_memberships_for_track("10") == 1


def test_playlist_delete_failure_preserves_state(tmp_path: Path):
    store = TidalStateStore(tmp_path / "tidal_state.db")
    _seed(
        store,
        track_id="10",
        playlist_name="Mix",
        playlist_id="p1",
        owned=False,
    )

    class FailingClient(FakeClient):
        def remove_playlist_tracks(self, playlist_id, track_ids):
            raise RuntimeError("delete failed")

    client = FailingClient()

    try:
        TidalReconciliationExecutor(
            client=client,
            state_store=store,
        ).execute([
            _decision(
                action=TidalReconcileAction.KEEP_FAVORITE_USER_OWNED,
            )
        ])
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected delete failure")

    assert store.count_memberships_for_track("10") == 1

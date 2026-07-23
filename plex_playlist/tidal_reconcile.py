from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from plex_playlist.tidal_account import TidalAccountClient
from plex_playlist.tidal_state import TidalStateStore


class TidalReconcileAction(str, Enum):
    KEEP = "KEEP"
    REMOVE_FROM_PLAYLIST = "REMOVE_FROM_PLAYLIST"
    REMOVE_FROM_PLAYLIST_AND_FAVORITES = "REMOVE_FROM_PLAYLIST_AND_FAVORITES"
    KEEP_FAVORITE_USER_OWNED = "KEEP_FAVORITE_USER_OWNED"
    KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION = (
        "KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION"
    )


@dataclass(frozen=True)
class TidalReconcileDecision:
    playlist_name: str
    playlist_id: str
    track_id: str
    action: TidalReconcileAction
    reason: str
    favorite_added_by_ppi: bool
    other_companion_count: int


class TidalReconciliationPlanner:
    """
    Compute destructive TIDAL reconciliation decisions without mutating TIDAL.
    """

    def __init__(self, state_store: TidalStateStore) -> None:
        self.state_store = state_store

    def plan(
        self,
        *,
        playlist_name: str,
        desired_track_ids: Iterable[str],
    ) -> list[TidalReconcileDecision]:
        desired = {
            str(track_id).strip()
            for track_id in desired_track_ids
            if str(track_id).strip()
        }

        decisions: list[TidalReconcileDecision] = []
        for membership in self.state_store.list_memberships_for_playlist(
            playlist_name
        ):
            track = self.state_store.get_track(membership.track_id)
            owned = bool(track.favorite_added_by_ppi) if track else False

            if membership.track_id in desired:
                decisions.append(
                    TidalReconcileDecision(
                        playlist_name=membership.playlist_name,
                        playlist_id=membership.playlist_id,
                        track_id=membership.track_id,
                        action=TidalReconcileAction.KEEP,
                        reason="Track remains required by this companion playlist.",
                        favorite_added_by_ppi=owned,
                        other_companion_count=0,
                    )
                )
                continue

            other_count = self.state_store.count_other_memberships_for_track(
                track_id=membership.track_id,
                excluding_playlist_name=membership.playlist_name,
            )

            if other_count > 0:
                action = (
                    TidalReconcileAction
                    .KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION
                )
                reason = (
                    "Track is stale in this companion playlist, but another "
                    f"PPI companion still references it ({other_count}). "
                    "Future destructive mode may remove only this playlist "
                    "membership and must keep the favorite."
                )
            elif owned:
                action = (
                    TidalReconcileAction
                    .REMOVE_FROM_PLAYLIST_AND_FAVORITES
                )
                reason = (
                    "Track is stale, no other PPI companion references it, "
                    "and PPI owns the favorite."
                )
            else:
                action = TidalReconcileAction.KEEP_FAVORITE_USER_OWNED
                reason = (
                    "Track is stale and no other PPI companion references it, "
                    "but PPI cannot prove ownership of the favorite. Future "
                    "destructive mode may remove it from this playlist only."
                )

            decisions.append(
                TidalReconcileDecision(
                    playlist_name=membership.playlist_name,
                    playlist_id=membership.playlist_id,
                    track_id=membership.track_id,
                    action=action,
                    reason=reason,
                    favorite_added_by_ppi=owned,
                    other_companion_count=other_count,
                )
            )

        return decisions


@dataclass(frozen=True)
class TidalReconcileExecutionResult:
    playlist_tracks_removed: tuple[str, ...]
    favorites_removed: tuple[str, ...]
    favorites_preserved: tuple[str, ...]


class TidalReconciliationExecutor:
    """
    Execute CP014 reconciliation decisions against TIDAL and local state.

    The executor never derives its own policy. It only acts on planner output.
    """

    def __init__(
        self,
        *,
        client: TidalAccountClient,
        state_store: TidalStateStore,
    ) -> None:
        self.client = client
        self.state_store = state_store

    def execute(
        self,
        decisions: Iterable[TidalReconcileDecision],
    ) -> TidalReconcileExecutionResult:
        playlist_removed: list[str] = []
        favorites_removed: list[str] = []
        favorites_preserved: list[str] = []

        for decision in decisions:
            if decision.action == TidalReconcileAction.KEEP:
                continue

            # Every stale decision removes this companion's playlist
            # membership, but only after the TIDAL DELETE succeeds.
            self.client.remove_playlist_tracks(
                decision.playlist_id,
                [decision.track_id],
            )
            self.state_store.remove_membership(
                playlist_name=decision.playlist_name,
                track_id=decision.track_id,
            )
            playlist_removed.append(decision.track_id)

            if (
                decision.action
                == TidalReconcileAction.REMOVE_FROM_PLAYLIST_AND_FAVORITES
            ):
                # Defensive re-check after state mutation: if another
                # companion still references the track, never unfavorite.
                remaining = self.state_store.count_memberships_for_track(
                    decision.track_id
                )
                track = self.state_store.get_track(decision.track_id)
                owned = bool(track.favorite_added_by_ppi) if track else False

                if remaining == 0 and owned:
                    self.client.remove_favorite_track(decision.track_id)
                    favorites_removed.append(decision.track_id)
                else:
                    favorites_preserved.append(decision.track_id)

            elif decision.action in {
                TidalReconcileAction.KEEP_FAVORITE_USER_OWNED,
                TidalReconcileAction.KEEP_FAVORITE_SHARED_BY_OTHER_COMPANION,
                TidalReconcileAction.REMOVE_FROM_PLAYLIST,
            }:
                favorites_preserved.append(decision.track_id)

        return TidalReconcileExecutionResult(
            playlist_tracks_removed=tuple(playlist_removed),
            favorites_removed=tuple(favorites_removed),
            favorites_preserved=tuple(favorites_preserved),
        )

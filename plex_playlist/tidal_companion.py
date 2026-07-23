from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from plex_playlist.tidal_account import (
    TidalAccountClient,
    TidalAccountError,
    TidalUserPlaylist,
)
from plex_playlist.tidal_state import TidalStateStore


@dataclass(frozen=True)
class TidalCompanionSyncResult:
    playlist: TidalUserPlaylist
    playlist_created: bool
    requested_track_count: int
    added_track_ids: tuple[str, ...]
    existing_track_ids: tuple[str, ...]
    favorite_added_track_ids: tuple[str, ...]
    favorite_existing_track_ids: tuple[str, ...]


class TidalCompanionPlaylistService:
    """
    Additive-only companion-playlist synchronization.

    This phase intentionally never removes tracks from TIDAL.
    """

    def __init__(
        self,
        client: TidalAccountClient,
        *,
        state_store: TidalStateStore | None = None,
    ) -> None:
        self.client = client
        self.state_store = state_store

    def find_or_create_playlist(
        self,
        name: str,
    ) -> tuple[TidalUserPlaylist, bool]:
        playlist_name = name.strip()
        if not playlist_name:
            raise ValueError("TIDAL companion playlist name must not be empty")

        matches = [
            playlist
            for playlist in self.client.list_owned_playlists()
            if playlist.name.casefold() == playlist_name.casefold()
        ]

        if len(matches) > 1:
            raise TidalAccountError(
                "Multiple owned TIDAL playlists have the requested companion "
                f"name {playlist_name!r}; refusing to choose one automatically."
            )

        if matches:
            return matches[0], False

        playlist = self.client.create_playlist(
            playlist_name,
            description=(
                "PPI companion playlist for tracks unavailable in the "
                "local Plex library."
            ),
            access_type="UNLISTED",
        )
        return playlist, True

    def add_missing_tracks(
        self,
        *,
        playlist_name: str,
        track_ids: Iterable[str],
        metadata_by_track_id: Mapping[str, tuple[str, str, str]] | None = None,
    ) -> TidalCompanionSyncResult:
        requested: list[str] = []
        seen: set[str] = set()

        for raw in track_ids:
            value = str(raw).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            requested.append(value)

        if not requested:
            raise ValueError(
                "At least one TIDAL track ID is required for companion sync"
            )

        playlist, created = self.find_or_create_playlist(playlist_name)
        current_ids = self.client.list_playlist_track_ids(
            playlist.playlist_id
        )

        missing = [
            track_id
            for track_id in requested
            if track_id not in current_ids
        ]

        if missing:
            self.client.add_playlist_tracks(
                playlist.playlist_id,
                missing,
            )

        favorite_ids = self.client.list_favorite_track_ids()
        favorite_missing = [
            track_id
            for track_id in requested
            if track_id not in favorite_ids
        ]

        for track_id in favorite_missing:
            self.client.add_favorite_track(track_id)

        if self.state_store is not None:
            metadata = metadata_by_track_id or {}
            favorite_added_set = set(favorite_missing)

            for track_id in requested:
                artist, title, album = metadata.get(
                    track_id,
                    ("", "", ""),
                )
                self.state_store.record_track(
                    track_id=track_id,
                    artist=artist,
                    title=title,
                    album=album,
                    favorite_added_by_ppi=track_id in favorite_added_set,
                )
                self.state_store.record_membership(
                    playlist_name=playlist.name,
                    playlist_id=playlist.playlist_id,
                    track_id=track_id,
                )

        return TidalCompanionSyncResult(
            playlist=playlist,
            playlist_created=created,
            requested_track_count=len(requested),
            added_track_ids=tuple(missing),
            existing_track_ids=tuple(
                track_id
                for track_id in requested
                if track_id in current_ids
            ),
            favorite_added_track_ids=tuple(favorite_missing),
            favorite_existing_track_ids=tuple(
                track_id
                for track_id in requested
                if track_id in favorite_ids
            ),
        )

"""
V2 Plex Client

Responsible ONLY for Plex I/O:
- loading library
- resolving tracks
- playlist management

No matching logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from plexapi.server import PlexServer

from plex_playlist.models import (
    LibraryTrack,
    MatchResult,
    PlaylistMode,
)

from plex_playlist.normalization import classify_version
from plexapi.exceptions import NotFound
from plex_playlist.runtime import ComponentHealth

import logging
import time

logger = logging.getLogger("plex_playlist")

@dataclass(frozen=True, slots=True)
class StalePlexMatch:
    rating_key: int
    artist: str
    title: str


@dataclass(slots=True)
class PlexResolutionResult:
    tracks: list
    stale_matches: list[StalePlexMatch]


# ============================================================
# Plex Client
# ============================================================

class PlexClient:
    """
    Thin wrapper around PlexAPI.

    Converts Plex objects into LibraryTrack
    and applies MatchResults back into playlists.
    """

    def __init__(self, url: str, token: str, library_name: str = "Music") -> None:
        self.url = url
        self.token = token
        self.library_name = library_name
        self.server = None
        self.library = None

    def is_available(self) -> ComponentHealth:
        """Verify Plex reachability and the configured music library."""
        try:
            server = PlexServer(self.url, self.token)
            library = server.library.section(self.library_name)
            library_type = getattr(library, "type", "")
            if library_type not in {"artist", "music"}:
                return ComponentHealth.unavailable(
                f"Configured Plex section '{self.library_name}' "
                "is not a music library"
            )
            self.server = server
            self.library = library
            return ComponentHealth.available_health(
                f"Plex reachable; music library "
                f"'{self.library_name}' available"
            )
        except Exception as exc:
            self.server = None
            self.library = None
            return ComponentHealth.unavailable(str(exc))

    def _require_available(self) -> None:
        if self.server is None or self.library is None:
            health = self.is_available()
            if not health.available:
                raise RuntimeError(f"Plex unavailable: {health.detail}")

    # --------------------------------------------------------
    # Library loading
    # --------------------------------------------------------

    def load_library(self) -> list[LibraryTrack]:
        
            
        #  Load full Plex library using materialization layer.
            

        self._require_available()

        logger.info("Loading Plex tracks via searchTracks()")

        plex_tracks = self.library.searchTracks()

        

        logger.info("Plex returned %d tracks", len(plex_tracks))

        # 🔥 MATERIALIZATION STEP (single-pass, no re-access)
        materialized = [
            self._materialize_track(item)
            for item in plex_tracks
        ]

 
        logger.info("Materialized %d tracks", len(materialized))

        return materialized

  
    def _materialize_track(self, item) -> LibraryTrack:
        """
        Convert Plex Track → LibraryTrack (no lazy access outside here)
        """

        title = getattr(item, "title", "") or ""

        return LibraryTrack(
            rating_key=int(item.ratingKey),
            guid=getattr(item, "guid", "") or "",

            artist=getattr(item, "grandparentTitle", "") or "",
            album_artist=getattr(item, "grandparentTitle", "") or "",

            album=getattr(item, "parentTitle", "") or "",
            title=title,

            duration=getattr(item, "duration", None),
            year=None,
            version=classify_version(title),
            file_path=self._extract_file_path(item),
        )
        
    # --------------------------------------------------------
    # Playlist operations
    # --------------------------------------------------------

    def get_playlist(self, name: str):
        """
        Return one exact-title playlist or None.

        Raise when duplicate exact-title playlists exist because
        modifying an arbitrary one would be unsafe.
        """

        self._require_available()

        try:
            candidates = self.server.playlists(
                title=name,
                playlistType="audio",
            )

        except Exception:
            logger.exception(
                "Unable to search Plex playlists for '%s'",
                name,
            )
            raise

        exact_matches = [
            playlist
            for playlist in candidates
            if playlist.title == name
        ]

        if not exact_matches:
            return None

        if len(exact_matches) > 1:
            raise RuntimeError(
                f"Multiple Plex playlists named '{name}' exist. "
                "Rename or delete the duplicates before continuing."
            )

        return exact_matches[0]

    
    def trim_playlist_fifo(
        self,
        *,
        name: str,
        max_tracks: int,
    ) -> dict[str, int]:
        """Trim a playlist from the front until it is at or below max_tracks."""

        if max_tracks < 0:
            raise ValueError("max_tracks must be 0 or greater")

        playlist = self.get_playlist(name)
        if playlist is None:
            raise RuntimeError(f"Playlist '{name}' does not exist")

        items = list(playlist.items())
        current = len(items)
        if max_tracks == 0 or current <= max_tracks:
            return {"current": current, "removed": 0, "final": current}

        remove_count = current - max_tracks
        # Use the actual playlist entry objects so duplicate occurrences remain
        # distinct and FIFO means playlist position, not unique track identity.
        playlist.removeItems(items[:remove_count])

        # Plex may briefly return stale playlist contents immediately after
        # removeItems(). Retry verification before declaring the trim incomplete.
        verification_attempts = 5
        verification_delay_seconds = 0.5

        final = current

        for attempt in range(verification_attempts):
            # Re-fetch the playlist rather than reusing the PlexAPI object that
            # performed removeItems(); that object may retain stale item state.
            refreshed_playlist = self.get_playlist(name)

            if refreshed_playlist is None:
                raise RuntimeError(
                    f"Playlist '{name}' disappeared while verifying trim"
                )

            final = len(list(refreshed_playlist.items()))

            if final <= max_tracks:
                break

            if attempt < verification_attempts - 1:
                time.sleep(verification_delay_seconds)

        if final > max_tracks:
            raise RuntimeError(
                f"Playlist trim incomplete for '{name}': "
                f"limit={max_tracks}, final={final}"
            )

        return {
            "current": current,
            "removed": remove_count,
            "final": final,
        }

    def update_playlist(
        self,
        #playlist_name: str,
        #tracks: list[LibraryTrack],
        name: str,
        tracks: list,
        mode: PlaylistMode,
    ):
        """
        Create or modify a Plex playlist using already-resolved
        PlexAPI Track objects.
        """

        playlist = self.get_playlist(name)
        plex_tracks = list(tracks)

        logger.info(
            "Updating playlist '%s' mode=%s tracks=%d",
            name,
            mode.name,
            len(plex_tracks),
        )

        if not plex_tracks:
            logger.warning(
                "No resolved tracks supplied for playlist '%s'",
                name,
            )
            return

        if playlist is None:
            created = self.server.createPlaylist(
                name,
                items=plex_tracks,
            )

            logger.info(
                "Playlist create summary:"
            )
            logger.info(
                "  Added     : %d",
                len(plex_tracks),
            )
            logger.info(
                "  Final     : %d",
                len(plex_tracks),
            )

            return created

        if mode == PlaylistMode.CREATE:
            raise RuntimeError(
                f"Playlist '{name}' already exists. "
                "Use --update, --replace, or --sync."
            )

        if mode == PlaylistMode.REPLACE:
            existing_items = playlist.items()

            if existing_items:
                playlist.removeItems(existing_items)

            playlist.addItems(plex_tracks)

            logger.info(
                "Playlist replace summary:"
            )
            logger.info(
                "  Removed         : %d",
                len(existing_items),
            )
            logger.info(
                "  Added           : %d",
                len(plex_tracks),
            )
            logger.info(
                "  Final playlist  : %d",
                len(plex_tracks),
            )

        elif mode in {
            PlaylistMode.UPDATE,
            PlaylistMode.SYNC,
        }:
            existing_items = playlist.items()

            existing_rating_keys = {
                int(item.ratingKey)
                for item in existing_items
            }

            new_items = [
                item
                for item in plex_tracks
                if int(item.ratingKey)
                not in existing_rating_keys
            ]

            already_present = (
                len(plex_tracks)
                - len(new_items)
            )

            if new_items:
                playlist.addItems(new_items)

            logger.info(
                "Playlist %s summary:",
                mode.name.lower(),
            )
            logger.info(
                "  Requested       : %d",
                len(plex_tracks),
            )
            logger.info(
                "  Already present : %d",
                already_present,
            )
            logger.info(
                "  Added           : %d",
                len(new_items),
            )
            logger.info(
                "  Final playlist  : %d",
                len(existing_items) + len(new_items),
            )

        else:
            raise ValueError(
                f"Unsupported playlist mode: {mode}"
            )

        return playlist

    # --------------------------------------------------------
    # Resolution layer (MatchResult → Plex objects)
    # --------------------------------------------------------

    def resolve_matches(
        self,
        results,
    ) -> PlexResolutionResult:
        """
        Resolve accepted LibraryTrack matches back to Plex track objects.

        A Plex 404 usually means the SQLite cache still references media
        removed since the most recent Plex scan/cache refresh. Such entries
        are returned as stale matches rather than raising a traceback.
        Unexpected Plex/API failures still propagate to the caller.
        """

        self._require_available()

        resolved_tracks = []
        stale_matches: list[StalePlexMatch] = []

        for result in results:
            matched = result.matched

            if matched is None:
                continue

            rating_key = int(matched.rating_key)

            try:
                item = self.library.fetchItem(rating_key)
            except NotFound:
                stale = StalePlexMatch(
                    rating_key=rating_key,
                    artist=str(matched.artist or ""),
                    title=str(matched.title or ""),
                )
                stale_matches.append(stale)
                logger.warning(
                    "Cached Plex item no longer exists: "
                    "%s - %s (rating key %s)",
                    stale.artist,
                    stale.title,
                    stale.rating_key,
                )
                continue

            resolved_tracks.append(item)

        logger.info(
            "Resolved %d matched tracks from Plex",
            len(resolved_tracks),
        )

        if stale_matches:
            logger.warning(
                "%d cached Plex match(es) could not be resolved. "
                "Run a Plex library scan, then rerun with "
                "--refresh-cache.",
                len(stale_matches),
            )

        return PlexResolutionResult(
            tracks=resolved_tracks,
            stale_matches=stale_matches,
        )

    # --------------------------------------------------------
    # Internal helper
    # --------------------------------------------------------

    def _extract_file_path(self, item) -> str:
        """
        Return the first media part's file path, when available.

        Filename metadata is used only for diagnostics.
        """

        try:
            media_items = getattr(item, "media", None) or []

            for media in media_items:
                parts = getattr(media, "parts", None) or []

                for part in parts:
                    file_path = getattr(part, "file", "") or ""

                    if file_path:
                        return str(file_path)

        except Exception:
            logger.debug(
                "Unable to read file path for Plex rating key %s",
                getattr(item, "ratingKey", "unknown"),
                exc_info=True,
            )

        return ""



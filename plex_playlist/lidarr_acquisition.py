from __future__ import annotations

from dataclasses import dataclass, replace
import logging
from typing import Any

from plex_playlist.lidarr_client import LidarrClient
from plex_playlist.lidarr_search_history import LidarrSearchHistoryStore
from plex_playlist.normalization import normalize_artist, normalize_title
from plex_playlist.rejected_terms import rejected_term_reason

logger = logging.getLogger("plex_playlist")

TRACK_ALREADY_AVAILABLE = "TRACK_ALREADY_AVAILABLE"
TRACK_NOT_IN_LIDARR_METADATA = "TRACK_NOT_IN_LIDARR_METADATA"
ARTIST_NOT_MANAGED = "ARTIST_NOT_MANAGED"
ARTIST_AMBIGUOUS = "ARTIST_AMBIGUOUS"
NO_ARTIST_CANDIDATE = "NO_ARTIST_CANDIDATE"
SEARCH_NOT_REQUESTED = "SEARCH_NOT_REQUESTED"
SEARCH_QUEUED = "SEARCH_QUEUED"
SEARCH_RECENTLY_REQUESTED = "SEARCH_RECENTLY_REQUESTED"
SEARCH_RETRY_QUEUED = "SEARCH_RETRY_QUEUED"
SEARCH_COMPLETED_FILE_AVAILABLE = "SEARCH_COMPLETED_FILE_AVAILABLE"
SEARCH_COMPLETED_NO_FILE = "SEARCH_COMPLETED_NO_FILE"
SEARCH_FAILED = "SEARCH_FAILED"
SEARCH_STATUS_UNAVAILABLE = "SEARCH_STATUS_UNAVAILABLE"
REJECTED_BY_CONFIGURATION = "REJECTED_BY_CONFIGURATION"


@dataclass(frozen=True, slots=True)
class LidarrResolution:
    best_candidate: dict[str, Any] | None
    managed_artist: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    albums: list[dict[str, Any]]
    tracks: list[dict[str, Any]]
    found_track: dict[str, Any] | None
    found_album: dict[str, Any] | None
    track_available: bool
    lidarr_artist_id: int | None
    album_id: int | None


@dataclass(frozen=True, slots=True)
class LidarrSearchDecision:
    requested: bool
    command_id: int | None
    search_status: str
    acquisition_status: str
    recommended_action: str
    refreshed_resolution: LidarrResolution | None = None


class LidarrAcquisitionService:
    def __init__(
        self,
        *,
        client: LidarrClient,
        history_store: LidarrSearchHistoryStore | None = None,
        remember_searches: bool = True,
        retry_after_days: float = 7.0,
        rejected_terms: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.client = client
        self.history_store = history_store
        self.remember_searches = remember_searches
        self.retry_after_days = retry_after_days
        self.rejected_terms = tuple(rejected_terms or ())
        self.lookup_cache: dict[str, list[dict[str, Any]]] = {}
        self.managed_cache: dict[str, dict[str, Any] | None] = {}
        self.artist_media_cache: dict[int, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
        self.searched_albums: dict[int, LidarrSearchDecision] = {}
        if history_store is not None:
            history_store.initialize()

    def resolve(self, *, requested_artist: str, requested_title: str) -> LidarrResolution:
        key = normalize_artist(requested_artist)
        if key not in self.lookup_cache:
            self.lookup_cache[key] = self.client.lookup_artist(requested_artist)
        candidates = self.lookup_cache[key]
        best, managed = self._resolve_artist(requested_artist, candidates)
        artist_id = _int_value(managed.get("id")) if managed else None
        albums: list[dict[str, Any]] = []
        tracks: list[dict[str, Any]] = []
        if artist_id is not None:
            if artist_id not in self.artist_media_cache:
                self.artist_media_cache[artist_id] = (
                    self.client.get_artist_albums(artist_id),
                    self.client.get_artist_tracks(artist_id),
                )
            albums, tracks = self.artist_media_cache[artist_id]
        track = _find_track(requested_title, tracks)
        album = _find_album(track, albums)
        available = _has_file(track) if track else False
        album_id = _int_value(album.get("id")) if album else None
        return LidarrResolution(
            best, managed, candidates, albums, tracks, track, album,
            available, artist_id, album_id,
        )

    def decide_search(
        self,
        *,
        requested_artist: str,
        resolution: LidarrResolution,
        search_missing_albums: bool,
        wait_for_search_seconds: float = 0.0,
        search_poll_interval_seconds: float = 2.0,
    ) -> LidarrSearchDecision:
        configured_rejection = rejected_term_reason(
            title=_track_title(resolution.found_track),
            album=_album_title(resolution.found_album),
            version=str(
                (resolution.found_track or {}).get("version", "") or ""
            ),
            rejected_terms=self.rejected_terms,
        )
        if configured_rejection is not None:
            return LidarrSearchDecision(
                False,
                None,
                "",
                REJECTED_BY_CONFIGURATION,
                configured_rejection,
            )

        if resolution.found_track is None:
            return LidarrSearchDecision(
                False, None, "", TRACK_NOT_IN_LIDARR_METADATA,
                "Review the artist's albums in Lidarr and identify the release",
            )
        if resolution.track_available:
            return LidarrSearchDecision(
                False, None, "", TRACK_ALREADY_AVAILABLE,
                "Refresh the Plex library or review Plex metadata",
            )
        if not search_missing_albums:
            return LidarrSearchDecision(
                False, None, "", SEARCH_NOT_REQUESTED,
                "Run with --lidarr-search to search the matching album",
            )
        if resolution.album_id is None:
            return LidarrSearchDecision(
                False, None, "", SEARCH_NOT_REQUESTED,
                "Matching album could not be searched",
            )

        album_id = resolution.album_id
        if album_id in self.searched_albums:
            return self.searched_albums[album_id]

        prior = self.history_store.get(album_id) if self.history_store else None
        if (
            self.remember_searches and self.history_store
            and not self.history_store.can_search(
                album_id=album_id,
                retry_after_days=self.retry_after_days,
            )
        ):
            decision = LidarrSearchDecision(
                False,
                prior.last_command_id if prior else None,
                prior.last_result if prior else "",
                SEARCH_RECENTLY_REQUESTED,
                "Album search was requested recently; retry interval has not elapsed",
            )
            self.searched_albums[album_id] = decision
            return decision

        decision = self._queue_search(
            requested_artist=requested_artist,
            resolution=resolution,
            prior_search_exists=prior is not None,
        )

        if (
            decision.command_id is not None
            and wait_for_search_seconds > 0
        ):
            decision = self._evaluate_completed_search(
                resolution=resolution,
                initial_decision=decision,
                wait_for_search_seconds=wait_for_search_seconds,
                search_poll_interval_seconds=(
                    search_poll_interval_seconds
                ),
            )
        self.searched_albums[album_id] = decision

        if (
            self.remember_searches and self.history_store
            and decision.acquisition_status
            in {
                SEARCH_QUEUED,
                SEARCH_RETRY_QUEUED,
                SEARCH_STATUS_UNAVAILABLE,
            }
        ):
            self.history_store.record_search(
                album_id=album_id,
                artist=requested_artist,
                album=_album_title(resolution.found_album),
                command_id=decision.command_id,
                result=decision.acquisition_status,
            )

        logger.info(
            "Lidarr album search: %s - %s "
            "(album ID %s, command ID %s, outcome %s)",
            requested_artist,
            _album_title(resolution.found_album),
            album_id,
            (
                decision.command_id
                if decision.command_id is not None
                else "unknown"
            ),
            decision.acquisition_status,
        )
        return decision

    def _queue_search(
        self,
        *,
        requested_artist: str,
        resolution: LidarrResolution,
        prior_search_exists: bool,
    ) -> LidarrSearchDecision:
        """Submit one Lidarr album search and classify the queue result."""

        album_id = resolution.album_id
        if album_id is None:
            return LidarrSearchDecision(
                False,
                None,
                "",
                SEARCH_NOT_REQUESTED,
                "Matching album could not be searched",
            )

        command = self.client.search_album(album_id)
        command_id = _int_value(command.get("id"))
        search_status = str(command.get("status", "") or "queued")

        if command_id is None:
            return LidarrSearchDecision(
                True,
                None,
                search_status,
                SEARCH_STATUS_UNAVAILABLE,
                "Lidarr accepted the search but returned no command ID",
            )

        if prior_search_exists:
            return LidarrSearchDecision(
                True,
                command_id,
                search_status,
                SEARCH_RETRY_QUEUED,
                "Album search re-queued in Lidarr",
            )

        return LidarrSearchDecision(
            True,
            command_id,
            search_status,
            SEARCH_QUEUED,
            "Album search queued in Lidarr",
        )

    def _evaluate_completed_search(
        self,
        *,
        resolution: LidarrResolution,
        initial_decision: LidarrSearchDecision,
        wait_for_search_seconds: float,
        search_poll_interval_seconds: float,
    ) -> LidarrSearchDecision:
        """
        Wait for a queued command and classify the completed result.

        The production path remains asynchronous because this method is
        called only when wait_for_search_seconds is greater than zero.
        """

        command_id = initial_decision.command_id
        if command_id is None:
            return initial_decision

        command_status = self.client.wait_for_command(
            command_id,
            timeout_seconds=wait_for_search_seconds,
            poll_interval_seconds=search_poll_interval_seconds,
        )

        if not command_status.completed:
            return LidarrSearchDecision(
                True,
                command_id,
                command_status.status,
                initial_decision.acquisition_status,
                (
                    "Lidarr search is still running; "
                    "retry on the next sync"
                ),
            )

        if not command_status.successful:
            return LidarrSearchDecision(
                True,
                command_id,
                command_status.status,
                SEARCH_FAILED,
                (
                    command_status.message
                    or "Lidarr album search command failed"
                ),
            )

        artist_id = resolution.lidarr_artist_id
        if artist_id is None:
            return LidarrSearchDecision(
                True,
                command_id,
                command_status.status,
                SEARCH_COMPLETED_NO_FILE,
                (
                    "Search completed but the managed artist "
                    "could not be refreshed"
                ),
            )

        refreshed_tracks = self.client.get_artist_tracks(artist_id)
        self.artist_media_cache[artist_id] = (
            resolution.albums,
            refreshed_tracks,
        )

        requested_title = _track_title(resolution.found_track)
        refreshed_track = _find_track(
            requested_title,
            refreshed_tracks,
        )

        refreshed_available = (
            refreshed_track is not None and _has_file(refreshed_track)
        )

        refreshed_resolution = replace(
            resolution,
            tracks=refreshed_tracks,
            found_track=refreshed_track,
            track_available=refreshed_available,
        )

        if refreshed_available:
            return LidarrSearchDecision(
                True,
                command_id,
                command_status.status,
                SEARCH_COMPLETED_FILE_AVAILABLE,
                "Track acquired; refresh Plex and retry matching",
                refreshed_resolution=refreshed_resolution,
            )

        return LidarrSearchDecision(
            True,
            command_id,
            command_status.status,
            SEARCH_COMPLETED_NO_FILE,
            (
                "Search completed but no track file is available; "
                "send to the TIDAL companion playlist"
            ),
            refreshed_resolution=refreshed_resolution,
        )

    def _resolve_artist(
        self,
        requested_artist: str,
        candidates: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        requested_key = normalize_artist(requested_artist)
        exact = [c for c in candidates if normalize_artist(_artist_name(c)) == requested_key]
        considered = exact if exact else (candidates if len(candidates) == 1 else [])
        if not considered:
            return None, None
        managed_matches = []
        for candidate in considered:
            mbid = str(candidate.get("foreignArtistId", "") or "")
            if not mbid:
                continue
            if mbid not in self.managed_cache:
                self.managed_cache[mbid] = self.client.get_managed_artist_by_mbid(mbid)
            managed = self.managed_cache[mbid]
            if managed is not None:
                managed_matches.append((candidate, managed))
        if len(managed_matches) == 1:
            return managed_matches[0]
        if len(considered) == 1:
            return considered[0], None
        return None, None


def _find_track(title: str, tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = normalize_title(title)
    matches = [t for t in tracks if normalize_title(_track_title(t)) == key]
    matches.sort(key=lambda item: (not _has_file(item), _int_value(item.get("id")) or 0))
    return matches[0] if matches else None


def _find_album(track: dict[str, Any] | None, albums: list[dict[str, Any]]) -> dict[str, Any] | None:
    if track is None:
        return None
    album_id = _int_value(track.get("albumId"))
    return next((a for a in albums if _int_value(a.get("id")) == album_id), None)


def _artist_name(item: dict[str, Any] | None) -> str:
    if item is None:
        return ""
    return str(item.get("artistName", "") or item.get("title", "") or "")


def _track_title(item: dict[str, Any] | None) -> str:
    if item is None:
        return ""
    return str(item.get("title", "") or item.get("trackTitle", "") or "")


def _album_title(item: dict[str, Any] | None) -> str:
    if item is None:
        return ""
    return str(item.get("title", "") or item.get("albumTitle", "") or "")


def _has_file(item: dict[str, Any]) -> bool:
    return bool(item.get("hasFile", False)) or (_int_value(item.get("trackFileId")) or 0) > 0


def _int_value(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None

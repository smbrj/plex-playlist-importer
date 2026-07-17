from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Callable

from plex_playlist.models import PlaylistEntry
from plex_playlist.normalization import normalize_artist, normalize_title
from plex_playlist.xmplaylist_client import (
    XMPlaylistClient,
    XMPlaylistError,
    XMPlaylistPlay,
    XMPlaylistStation,
)
from plex_playlist.xmplaylist_state import (
    XMPlaylistBackfillState,
    XMPlaylistStateStore,
)

logger = logging.getLogger("plex_playlist")


@dataclass(frozen=True, slots=True)
class XMPlaylistIngestion:
    station: XMPlaylistStation
    entries: tuple[PlaylistEntry, ...]
    requests_made: int
    backfill_complete: bool
    partial: bool
    rate_limited: bool
    next_cursor: str | None

    @property
    def playlist_name(self) -> str:
        return self.station.plex_playlist_name


def ingest_station(
    *,
    client: XMPlaylistClient,
    station_number: int,
    hours: int = 8,
    max_requests: int = 10,
    max_tracks: int | None = None,
    state_store: XMPlaylistStateStore | None = None,
    now_factory: Callable[[], datetime] | None = None,
) -> XMPlaylistIngestion:
    """
    Incrementally ingest one station while respecting a request budget.

    Request counting includes station resolution. The remaining budget is
    used for history pages. Partial results are persisted and resumed on the
    next run when a state store is supplied.
    """

    if not 1 <= int(hours) <= 720:
        raise ValueError("hours must be between 1 and 720")
    if int(max_requests) < 2:
        raise ValueError(
            "max_requests must be at least 2 "
            "(one station-list request plus one history request)"
        )
    if max_tracks is not None and int(max_tracks) < 1:
        raise ValueError("max_tracks must be at least 1")

    now = (
        now_factory()
        if now_factory is not None
        else datetime.now(timezone.utc)
    )
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    cutoff = now - timedelta(hours=int(hours))
    cutoff_iso = cutoff.isoformat()

    if state_store is not None:
        state_store.initialize()

    station = client.resolve_station(int(station_number))
    requests_made = 1

    previous_state = (
        state_store.load_state(station.number)
        if state_store is not None
        else None
    )

    if (
        previous_state is not None
        and previous_state.history_hours != int(hours)
    ):
        logger.info(
            "XMPlaylist history window changed from %d to %d hours; "
            "resetting saved backfill state",
            previous_state.history_hours,
            hours,
        )
        state_store.reset_station(station.number)
        previous_state = None

    cursor = (
        previous_state.next_cursor
        if previous_state is not None
        and not previous_state.backfill_complete
        else None
    )

    oldest_timestamp = (
        previous_state.oldest_timestamp
        if previous_state is not None
        else None
    )
    backfill_complete = bool(
        previous_state.backfill_complete
        if previous_state is not None
        else False
    )
    rate_limited = False
    track_limit_reached = False
    seen_cursors: set[str] = set()
    run_tracks: dict[tuple[str, str], tuple[str, str]] = {}

    while requests_made < int(max_requests):
        try:
            page = client.get_history_page(station, last=cursor)
        except XMPlaylistError as exc:
            if "rate limit exceeded" not in str(exc).casefold():
                raise
            logger.warning("%s", exc)
            rate_limited = True
            break

        requests_made += 1
        reached_cutoff = False

        for play in page.plays:
            played_at = _parse_timestamp(play.timestamp)
            played_iso = played_at.isoformat()

            if oldest_timestamp is None or played_iso < oldest_timestamp:
                oldest_timestamp = played_iso

            if played_at < cutoff:
                reached_cutoff = True
                continue

            artist = _primary_artist(play)
            title = play.title.strip()
            if not artist or not title:
                continue

            artist_key = normalize_artist(artist)
            title_key = normalize_title(title)
            if not artist_key or not title_key:
                continue

            track_key = (artist_key, title_key)
            run_tracks.setdefault(track_key, (artist, title))

            if state_store is not None:
                state_store.upsert_track(
                    station_number=station.number,
                    artist_key=artist_key,
                    title_key=title_key,
                    artist=artist,
                    title=title,
                    last_seen_timestamp=played_iso,
                )

            if (
                max_tracks is not None
                and len(run_tracks) >= int(max_tracks)
            ):
                track_limit_reached = True
                break

        if track_limit_reached:
            cursor = page.next_cursor
            break

        if reached_cutoff or page.next_cursor is None:
            backfill_complete = True
            cursor = None
            break

        if page.next_cursor in seen_cursors:
            logger.warning(
                "XMPlaylist repeated history cursor %s; "
                "stopping pagination",
                page.next_cursor,
            )
            cursor = page.next_cursor
            break

        seen_cursors.add(page.next_cursor)
        cursor = page.next_cursor

    if state_store is not None:
        state_store.delete_before(
            station_number=station.number,
            cutoff_timestamp=cutoff_iso,
        )
        state_store.save_state(
            XMPlaylistBackfillState(
                station_number=station.number,
                station_name=station.name,
                station_deeplink=station.deeplink,
                history_hours=int(hours),
                next_cursor=cursor,
                oldest_timestamp=oldest_timestamp,
                backfill_complete=backfill_complete,
            )
        )
        track_pairs = (
            list(run_tracks.values())[: int(max_tracks)]
            if max_tracks is not None
            else state_store.load_tracks(station.number)
        )
    else:
        # Stateless mode exposes tracks observed during this run.
        track_pairs = list(run_tracks.values())
        if max_tracks is not None:
            track_pairs = track_pairs[: int(max_tracks)]

    entries = tuple(
        PlaylistEntry(
            sequence=sequence,
            artist=artist,
            title=title,
        )
        for sequence, (artist, title) in enumerate(
            track_pairs,
            start=1,
        )
    )

    partial = not backfill_complete and not track_limit_reached
    stop_reason = (
        "TRACK_LIMIT_REACHED"
        if track_limit_reached
        else (
            "RATE_LIMITED"
            if rate_limited
            else (
                "HISTORY_COMPLETE"
                if backfill_complete
                else "REQUEST_LIMIT_REACHED"
            )
        )
    )
    logger.info(
        "XMPlaylist ingestion: channel %s %s, %d unique tracks, "
        "%d requests, backfill %s%s; stop reason=%s",
        station.number,
        station.name,
        len(entries),
        requests_made,
        "complete" if backfill_complete else "partial",
        ", rate limited" if rate_limited else "",
        stop_reason,
    )

    if track_limit_reached:
        logger.info(
            "XMPlaylist track target reached: %d unique tracks this run",
            len(entries),
        )

    if partial and requests_made >= int(max_requests):
        logger.info(
            "XMPlaylist request limit reached: %d requests this run; "
            "backfill will resume next run",
            requests_made,
        )

    return XMPlaylistIngestion(
        station=station,
        entries=entries,
        requests_made=requests_made,
        backfill_complete=backfill_complete,
        partial=partial,
        rate_limited=rate_limited,
        next_cursor=cursor,
    )


def _primary_artist(play: XMPlaylistPlay) -> str:
    return play.artists[0].strip() if play.artists else ""


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Invalid XMPlaylist timestamp: {value!r}"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)

from __future__ import annotations

import logging
from typing import Iterable

from plex_playlist.normalization import canonical_artist_key, normalize_title
from plex_playlist.tidal_reconcile import TidalReconcileAction

logger = logging.getLogger("plex_playlist")


def playlist_trim_preview(
    *,
    current_rating_keys: list[int],
    requested_rating_keys: list[int],
    trim_limit: int,
) -> dict[str, int]:
    """Calculate exact CREATE/UPDATE trim counts without modifying Plex."""
    if trim_limit < 0:
        raise ValueError("trim_limit must be 0 or greater")

    existing = list(current_rating_keys)
    existing_set = set(existing)
    requested_unique: list[int] = []
    seen: set[int] = set()
    for rating_key in requested_rating_keys:
        if rating_key in seen:
            continue
        seen.add(rating_key)
        requested_unique.append(rating_key)

    new_unique = sum(1 for key in requested_unique if key not in existing_set)
    after_update = len(existing) + new_unique
    remove = 0 if trim_limit == 0 else max(0, after_update - trim_limit)
    return {
        "current": len(existing),
        "new_unique": new_unique,
        "after_update": after_update,
        "remove": remove,
        "final": after_update - remove,
    }


def filter_tidal_reconciliation_for_final_plex_membership(
    *,
    decisions: Iterable,
    state_store,
    playlist_items: Iterable,
    artist_aliases: dict[str, str],
):
    """Suppress destructive handoff if the local track is absent post-trim."""
    final_keys = set()
    for item in playlist_items:
        artist = str(getattr(item, "grandparentTitle", "") or "")
        title = str(getattr(item, "title", "") or "")
        final_keys.add((
            canonical_artist_key(artist, artist_aliases),
            normalize_title(title),
        ))

    safe = []
    for decision in decisions:
        if decision.action == TidalReconcileAction.KEEP:
            safe.append(decision)
            continue

        tidal_track = state_store.get_track(decision.track_id)
        if tidal_track is None:
            logger.info(
                "TIDAL destructive handoff suppressed: track=%s; "
                "local ownership metadata unavailable",
                decision.track_id,
            )
            continue

        key = (
            canonical_artist_key(tidal_track.artist, artist_aliases),
            normalize_title(tidal_track.title),
        )
        if key in final_keys:
            safe.append(decision)
        else:
            logger.info(
                "TIDAL destructive handoff suppressed after Plex trim: "
                "track=%s; final Plex playlist does not contain %s - %s",
                decision.track_id,
                tidal_track.artist,
                tidal_track.title,
            )

    return safe

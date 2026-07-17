"""
search_index.py

Persistent in-memory search index for the Plex library.

The SearchIndex provides O(1) lookups by normalized metadata and is
constructed from the normalized LibraryTrack records loaded from the
SQLite cache.

The matcher should interact with SearchIndex rather than raw lists of
tracks.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from plex_playlist.models import LibraryTrack
from plex_playlist.normalization import (
    normalize_key,
    title_tokens,
)

from math import ceil


@dataclass(slots=True)
class SearchIndex:
    """
    Immutable search index used by the matcher.

    Most lookups intentionally return lists because duplicate tracks
    (same artist/title on multiple albums) are common in music libraries.
    """

    all_tracks: list[LibraryTrack] = field(default_factory=list)

    by_artist: dict[str, list[LibraryTrack]] = field(default_factory=dict)

    by_title: dict[str, list[LibraryTrack]] = field(default_factory=dict)

    by_title_token: dict[str, list[LibraryTrack]] = field(
        default_factory=dict
    )

    by_album: dict[str, list[LibraryTrack]] = field(default_factory=dict)

    by_artist_title: dict[str, list[LibraryTrack]] = field(default_factory=dict)

    by_guid: dict[str, LibraryTrack] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        tracks: Iterable[LibraryTrack],
    ) -> "SearchIndex":
        """
        Build a SearchIndex from LibraryTrack objects.

        This is typically called after loading tracks from the SQLite cache.
        """

        artist = defaultdict(list)
        title = defaultdict(list)
        title_token = defaultdict(list)
        album = defaultdict(list)
        artist_title = defaultdict(list)
        guid = {}

        track_list = []

        for track in tracks:

            track_list.append(track)

            artist_key = normalize_key(track.artist)
            title_key = normalize_key(track.title)
            for token in title_tokens(track.title):
                title_token[token].append(track)
            album_key = normalize_key(track.album)

            combined_key = f"{artist_key}|{title_key}"

            artist[artist_key].append(track)
            title[title_key].append(track)
            album[album_key].append(track)
            artist_title[combined_key].append(track)

            if track.guid:
                guid[track.guid] = track

        return cls(
            all_tracks=track_list,
            by_artist=dict(artist),
            by_title=dict(title),
            by_title_token=dict(title_token),
            by_album=dict(album),
            by_artist_title=dict(artist_title),
            by_guid=guid,
        )

    def artist_matches(
        self,
        artist: str,
    ) -> list[LibraryTrack]:

        return self.by_artist.get(
            normalize_key(artist),
            [],
        )

    def title_matches(
        self,
        title: str,
    ) -> list[LibraryTrack]:

        return self.by_title.get(
            normalize_key(title),
            [],
        )

    def title_token_matches(
        self,
        title: str,
    ) -> list[LibraryTrack]:
        """
        Return tracks sharing a meaningful portion of the requested
        title tokens.

        This broadens candidate discovery without accepting a match.
        The matcher title gate still determines whether candidates are
        actually similar enough.
        """

        requested_tokens = title_tokens(title)

        if not requested_tokens:
            return []

        #
        # Require at least half the requested tokens.
        #
        # One-token titles require that one token.
        #

        required_overlap = max(
            1,
            ceil(len(requested_tokens) * 0.5),
        )

        overlap_counts: dict[int, int] = {}
        tracks_by_key: dict[int, LibraryTrack] = {}

        for token in requested_tokens:
            for track in self.by_title_token.get(token, []):
                rating_key = track.rating_key

                tracks_by_key[rating_key] = track
                overlap_counts[rating_key] = (
                    overlap_counts.get(rating_key, 0) + 1
                )

        matches = [
            tracks_by_key[rating_key]
            for rating_key, overlap in overlap_counts.items()
            if overlap >= required_overlap
        ]

        return matches

    def album_matches(
        self,
        album: str,
    ) -> list[LibraryTrack]:

        return self.by_album.get(
            normalize_key(album),
            [],
        )

    def artist_title_matches(
        self,
        artist: str,
        title: str,
    ) -> list[LibraryTrack]:

        key = (
            normalize_key(artist)
            + "|"
            + normalize_key(title)
        )

        return self.by_artist_title.get(
            key,
            [],
        )

    def guid_match(
        self,
        guid: str,
    ) -> LibraryTrack | None:

        return self.by_guid.get(guid)

    @property
    def track_count(self) -> int:
        return len(self.all_tracks)

    def album_artist_matches(
        self,
        artist: str,
    ) -> list[LibraryTrack]:

        key = normalize_key(artist)

        return [
            track
            for track in self.all_tracks
            if normalize_key(track.album_artist) == key
        ] 
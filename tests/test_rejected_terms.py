from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from plex_playlist.lidarr_acquisition import REJECTED_BY_CONFIGURATION
from plex_playlist.lidarr_reporting import build_lidarr_diagnostics
from plex_playlist.matcher import match_playlist
from plex_playlist.models import LibraryTrack, MatchingConfig, PlaylistEntry
from plex_playlist.rejected_terms import parse_rejected_terms, rejected_term_reason
from plex_playlist.search_index import SearchIndex
from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import (
    choose_tidal_match,
    tidal_candidate_rejection_reason,
)


def plex_track(*, key: int, title: str = "Peg", album: str = "Aja", version: str = "studio") -> LibraryTrack:
    return LibraryTrack(
        rating_key=key,
        guid=f"test://{key}",
        artist="Steely Dan",
        album_artist="Steely Dan",
        album=album,
        title=title,
        duration=240_000,
        year=1977,
        version=version,
    )


def tidal_track(*, track_id: str = "1", title: str = "Peg", album: str = "Aja", version: str = "") -> TidalTrackCandidate:
    return TidalTrackCandidate(
        track_id=track_id,
        artist="Steely Dan",
        title=title,
        album=album,
        quality="LOSSLESS",
        version=version,
    )


def test_parse_rejected_terms_normalizes_and_deduplicates() -> None:
    assert parse_rejected_terms(" Karaoke, tribute-band, KARAOKE ") == (
        "karaoke",
        "tribute band",
    )


def test_rejected_term_reason_is_field_specific_and_punctuation_tolerant() -> None:
    assert rejected_term_reason(
        album="The KARAOKE-Version!",
        rejected_terms=("karaoke version",),
    ) == "rejected term 'karaoke version' found in album title"


def test_rejected_term_does_not_match_inside_unrelated_word() -> None:
    assert rejected_term_reason(
        title="Karaokesque",
        rejected_terms=("karaoke",),
    ) is None


def test_plex_rejects_karaoke_album_before_scoring() -> None:
    index = SearchIndex.build([
        plex_track(key=1, album="Aja Karaoke"),
    ])
    session = match_playlist(
        playlist=[PlaylistEntry(sequence=1, artist="Steely Dan", title="Peg")],
        index=index,
        config=MatchingConfig(workers=1, rejected_terms=("karaoke",)),
    )
    result = session.results[0]
    assert result.matched is None
    assert "rejected term 'karaoke' found in album title" in result.reason


def test_plex_clean_candidate_wins_when_karaoke_candidate_is_present() -> None:
    index = SearchIndex.build([
        plex_track(key=1, album="Aja Karaoke"),
        plex_track(key=2, album="Aja"),
    ])
    session = match_playlist(
        playlist=[PlaylistEntry(sequence=1, artist="Steely Dan", title="Peg")],
        index=index,
        config=MatchingConfig(workers=1, rejected_terms=("karaoke",)),
    )
    assert session.results[0].matched.rating_key == 2


def test_rejected_terms_take_precedence_over_preferred_versions() -> None:
    index = SearchIndex.build([
        plex_track(key=1, version="karaoke"),
        plex_track(key=2, version="studio"),
    ])
    session = match_playlist(
        playlist=[PlaylistEntry(sequence=1, artist="Steely Dan", title="Peg")],
        index=index,
        config=MatchingConfig(
            workers=1,
            preferred_versions=["karaoke", "studio"],
            rejected_terms=("karaoke",),
        ),
    )
    assert session.results[0].matched.rating_key == 2


def test_tidal_rejects_karaoke_album_before_quality_ranking() -> None:
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            tidal_track(track_id="karaoke", album="Aja Karaoke"),
            tidal_track(track_id="clean", album="Aja"),
        ],
        quality_preference=("LOSSLESS",),
        rejected_terms=("karaoke",),
    )
    assert decision.matched.track_id == "clean"


def test_tidal_rejection_reason_names_triggering_field() -> None:
    reason = tidal_candidate_rejection_reason(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidate=tidal_track(title="Peg (Karaoke Version)"),
        rejected_terms=("karaoke",),
    )
    assert reason == "rejected term 'karaoke' found in track title"


def test_tidal_cache_is_separated_by_rejected_term_policy(tmp_path: Path) -> None:
    cache = TidalSearchCache(tmp_path / "tidal.db")
    cache.initialize()
    cache.put_match(
        "Steely Dan",
        "Peg",
        tidal_track(),
        allow_explicit=True,
        rejected_terms=(),
    )
    assert cache.get(
        "Steely Dan", "Peg", allow_explicit=True, rejected_terms=()
    ).found is True
    assert cache.get(
        "Steely Dan", "Peg", allow_explicit=True, rejected_terms=("karaoke",)
    ).found is False


def _unmatched() -> SimpleNamespace:
    return SimpleNamespace(
        entry=SimpleNamespace(sequence=1, artist="Sam Cooke", title="Shake"),
        matched=None,
        reason="No candidates",
    )


def test_lidarr_karaoke_album_is_not_searched() -> None:
    client = Mock()
    client.lookup_artist.return_value = [
        {"artistName": "Sam Cooke", "foreignArtistId": "mbid"}
    ]
    client.get_managed_artist_by_mbid.return_value = {
        "id": 42,
        "artistName": "Sam Cooke",
        "foreignArtistId": "mbid",
    }
    client.get_artist_albums.return_value = [
        {"id": 100, "title": "Shake Karaoke"}
    ]
    client.get_artist_tracks.return_value = [
        {"id": 200, "albumId": 100, "title": "Shake", "hasFile": False}
    ]

    rows = build_lidarr_diagnostics(
        results=[_unmatched()],
        client=client,
        search_missing_albums=True,
        rejected_terms=("karaoke",),
    )
    assert rows[0].acquisition_status == REJECTED_BY_CONFIGURATION
    assert rows[0].recommended_action == "rejected term 'karaoke' found in album title"
    client.search_album.assert_not_called()



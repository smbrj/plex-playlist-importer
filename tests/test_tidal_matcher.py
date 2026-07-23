from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import (
    choose_tidal_match,
    qualifying_candidates,
)


def candidate(
    *,
    track_id="1",
    artist="Steely Dan",
    title="Peg",
    album="Aja",
    quality=None,
):
    return TidalTrackCandidate(
        track_id=track_id,
        artist=artist,
        title=title,
        album=album,
        quality=quality,
    )


def test_exact_artist_and_title_are_required():
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            candidate(artist="Steely Dann"),
            candidate(title="Peggy"),
        ],
    )
    assert decision.matched is None


def test_configured_artist_alias_is_accepted():
    decision = choose_tidal_match(
        requested_artist="Doobie Brothers",
        requested_title="Listen to the Music",
        candidates=[
            candidate(
                artist="The Doobie Brothers",
                title="Listen to the Music",
            )
        ],
        artist_aliases={
            "Doobie Brothers": "The Doobie Brothers"
        },
    )
    assert decision.matched is not None


def test_album_does_not_participate_in_match():
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[candidate(album="Greatest Hits")],
    )
    assert decision.matched is not None


def test_remaster_mono_and_stereo_are_accepted():
    for title in (
        "Peg (2011 Remastered)",
        "Peg (Mono Mix)",
        "Peg (Stereo Mix)",
    ):
        accepted = qualifying_candidates(
            requested_artist="Steely Dan",
            requested_title="Peg",
            candidates=[candidate(title=title)],
        )
        assert len(accepted) == 1, title


def test_non_studio_variants_are_rejected():
    for title in (
        "Peg (Live)",
        "Peg Demo",
        "Peg Take 2",
        "Peg Radio Edit",
        "Peg Extended",
        "Peg Instrumental",
    ):
        accepted = qualifying_candidates(
            requested_artist="Steely Dan",
            requested_title="Peg",
            candidates=[candidate(title=title)],
        )
        assert accepted == [], title


def test_first_qualifying_result_is_temporarily_selected():
    # Phase 1: quality ordering is intentionally deferred until live payload
    # verification confirms TIDAL's current official quality values.
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            candidate(track_id="low", quality="LOW"),
            candidate(track_id="high", quality="HIGH"),
        ],
    )
    assert decision.matched.track_id == "low"

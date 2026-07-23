from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import choose_tidal_match, tidal_quality_rank


def c(track_id, quality):
    return TidalTrackCandidate(
        track_id=track_id,
        artist="Sublime",
        title="What I Got",
        album="Sublime",
        quality=quality,
    )


def test_default_atmos_beats_hires_lossless():
    decision = choose_tidal_match(
        requested_artist="Sublime",
        requested_title="What I Got",
        candidates=[
            c("hires", "HIRES_LOSSLESS,LOSSLESS"),
            c("atmos", "DOLBY_ATMOS"),
        ],
    )
    assert decision.matched.track_id == "atmos"


def test_config_can_reverse_atmos_and_hires():
    decision = choose_tidal_match(
        requested_artist="Sublime",
        requested_title="What I Got",
        candidates=[
            c("atmos", "DOLBY_ATMOS"),
            c("hires", "HIRES_LOSSLESS,LOSSLESS"),
        ],
        quality_preference=(
            "HIRES_LOSSLESS",
            "DOLBY_ATMOS",
            "LOSSLESS",
        ),
    )
    assert decision.matched.track_id == "hires"


def test_multiple_tags_use_highest_configured_tag():
    assert tidal_quality_rank(
        c("x", "HIRES_LOSSLESS,LOSSLESS"),
        ("DOLBY_ATMOS", "HIRES_LOSSLESS", "LOSSLESS"),
    ) > tidal_quality_rank(
        c("y", "LOSSLESS"),
        ("DOLBY_ATMOS", "HIRES_LOSSLESS", "LOSSLESS"),
    )


def test_unlisted_quality_ranks_below_listed_quality():
    assert tidal_quality_rank(
        c("unknown", "SOMETHING_NEW"),
        ("DOLBY_ATMOS", "HIRES_LOSSLESS", "LOSSLESS"),
    ) == 0


def test_equal_quality_preserves_api_order():
    decision = choose_tidal_match(
        requested_artist="Sublime",
        requested_title="What I Got",
        candidates=[
            c("first", "LOSSLESS"),
            c("second", "LOSSLESS"),
        ],
    )
    assert decision.matched.track_id == "first"

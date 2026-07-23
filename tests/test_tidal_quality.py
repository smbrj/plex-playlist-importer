from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import choose_tidal_match, tidal_quality_rank


def c(track_id, quality):
    return TidalTrackCandidate(
        track_id=track_id,
        artist="Steely Dan",
        title="Peg",
        album="Aja",
        quality=quality,
    )


def test_hires_lossless_beats_lossless():
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            c("lossless", "LOSSLESS"),
            c("hires", "HIRES_LOSSLESS,LOSSLESS"),
        ],
    )
    assert decision.matched.track_id == "hires"


def test_unknown_quality_does_not_beat_recognized_lossless():
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            c("unknown", "SOMETHING_NEW"),
            c("lossless", "LOSSLESS"),
        ],
    )
    assert decision.matched.track_id == "lossless"


def test_equal_quality_preserves_api_order():
    decision = choose_tidal_match(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[
            c("first", "LOSSLESS"),
            c("second", "LOSSLESS"),
        ],
    )
    assert decision.matched.track_id == "first"


def test_quality_rank_handles_multiple_tags():
    assert tidal_quality_rank(c("x", "HIRES_LOSSLESS,LOSSLESS")) > tidal_quality_rank(
        c("y", "LOSSLESS")
    )

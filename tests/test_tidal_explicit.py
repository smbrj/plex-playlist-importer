from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_matcher import (
    choose_tidal_match,
    qualifying_candidates,
    tidal_candidate_rejection_reason,
)


def candidate(
    track_id: str,
    *,
    quality: str = "LOSSLESS",
    explicit: bool = False,
) -> TidalTrackCandidate:
    return TidalTrackCandidate(
        track_id=track_id,
        artist="Test Artist",
        title="Test Song",
        album="Test Album",
        quality=quality,
        explicit=explicit,
    )


def test_explicit_candidate_is_allowed_when_configuration_true():
    explicit = candidate("explicit", explicit=True)

    accepted = qualifying_candidates(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[explicit],
        allow_explicit=True,
    )

    assert accepted == [explicit]


def test_explicit_candidate_is_rejected_when_configuration_false():
    explicit = candidate("explicit", explicit=True)

    accepted = qualifying_candidates(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[explicit],
        allow_explicit=False,
    )

    assert accepted == []
    assert tidal_candidate_rejection_reason(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidate=explicit,
        allow_explicit=False,
    ) == "explicit content rejected by configuration"


def test_clean_candidate_remains_eligible_when_explicit_is_disabled():
    clean = candidate("clean", explicit=False)

    accepted = qualifying_candidates(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[clean],
        allow_explicit=False,
    )

    assert accepted == [clean]


def test_explicit_filter_runs_before_quality_ranking():
    explicit_atmos = candidate(
        "explicit-atmos",
        quality="DOLBY_ATMOS",
        explicit=True,
    )
    clean_lossless = candidate(
        "clean-lossless",
        quality="LOSSLESS",
        explicit=False,
    )

    allowed = choose_tidal_match(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[clean_lossless, explicit_atmos],
        allow_explicit=True,
    )
    blocked = choose_tidal_match(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[clean_lossless, explicit_atmos],
        allow_explicit=False,
    )

    assert allowed.matched == explicit_atmos
    assert blocked.matched == clean_lossless

from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_diagnostics import format_tidal_search_results


def test_diagnostic_shows_explicit_and_exact_configuration_reason():
    candidate = TidalTrackCandidate(
        track_id="123",
        artist="Test Artist",
        title="Test Song",
        album="Test Album",
        quality="LOSSLESS",
        explicit=True,
    )

    text = format_tidal_search_results(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[candidate],
        accepted=[],
        allow_explicit=False,
    )

    assert "Explicit : YES" in text
    assert "Reason   : explicit content rejected by configuration" in text


def test_diagnostic_shows_no_for_non_explicit_candidate():
    candidate = TidalTrackCandidate(
        track_id="123",
        artist="Test Artist",
        title="Test Song",
        album="Test Album",
        explicit=False,
    )

    text = format_tidal_search_results(
        requested_artist="Test Artist",
        requested_title="Test Song",
        candidates=[candidate],
        accepted=[candidate],
        allow_explicit=False,
    )

    assert "Explicit : NO" in text
    assert "explicit content rejected by configuration" not in text

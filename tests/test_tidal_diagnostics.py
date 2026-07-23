from plex_playlist.tidal_client import TidalTrackCandidate
from plex_playlist.tidal_diagnostics import format_tidal_search_results


def candidate(track_id, artist, title, album, quality=None):
    return TidalTrackCandidate(
        track_id=track_id,
        artist=artist,
        title=title,
        album=album,
        quality=quality,
    )


def test_format_marks_accepted_and_rejected_candidates():
    accepted_candidate = candidate(
        "1", "Steely Dan", "Peg", "Aja", "HI_RES_LOSSLESS"
    )
    rejected_candidate = candidate(
        "2", "Steely Dan", "Peg (Live)", "Live Album", "LOSSLESS"
    )

    output = format_tidal_search_results(
        requested_artist="Steely Dan",
        requested_title="Peg",
        candidates=[accepted_candidate, rejected_candidate],
        accepted=[accepted_candidate],
    )

    assert "Strict matches: 1" in output
    assert "[1] ACCEPT" in output
    assert "[2] REJECT" in output
    assert "HI_RES_LOSSLESS" in output
    assert "Peg (Live)" in output


def test_format_handles_no_candidates():
    output = format_tidal_search_results(
        requested_artist="Nobody",
        requested_title="Nothing",
        candidates=[],
        accepted=[],
    )

    assert "Candidates returned: 0" in output
    assert "No TIDAL track candidates returned." in output

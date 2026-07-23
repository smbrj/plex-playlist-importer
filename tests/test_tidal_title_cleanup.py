from plex_playlist.tidal_service import tidal_requested_title


def test_tidal_title_strips_trailing_two_digit_parenthetical():
    assert tidal_requested_title("Tootsee Roll (94)") == "Tootsee Roll"


def test_tidal_title_strips_trailing_four_digit_parenthetical():
    assert tidal_requested_title("What I Got (1996)") == "What I Got"


def test_tidal_title_preserves_meaningful_parenthetical_text():
    assert tidal_requested_title("I Do (Cherish You)") == "I Do (Cherish You)"


def test_tidal_title_preserves_non_trailing_numeric_text():
    assert tidal_requested_title("99 Luftballons") == "99 Luftballons"

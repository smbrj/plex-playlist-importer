import pytest

from plex_playlist.normalization import (
    artist_lookup_names,
    canonical_artist_key,
    classify_version,
    fold_unicode,
    normalize_album,
    normalize_artist,
    normalize_key,
    normalize_text,
    normalize_title,
    title_tokens,
)


def test_fold_unicode_removes_accents_and_casefolds():
    assert fold_unicode("Beyoncé — Mötley Crüe") == "beyonce - motley crue"


def test_fold_unicode_transliterates_non_decomposing_letters():
    assert fold_unicode("Bjørk & Straße") == "bjork & strasse"


def test_normalize_text_collapses_punctuation_and_spacing():
    assert normalize_text("  What's   Going-On?!  ") == "what s going on"


def test_normalize_text_removes_parenthetical_version_noise():
    assert normalize_text("Song Title (2011 Remastered)") == "song title"


def test_normalize_text_preserves_meaningful_parenthetical_text():
    assert normalize_text("Song Title (Reprise)") == "song title reprise"


def test_normalize_artist_removes_featured_artist_suffix():
    assert normalize_artist("Artist feat. Guest") == "artist"
    assert normalize_artist("Artist Featuring Guest") == "artist"


def test_normalize_title_preserves_legitimate_live_word():
    assert normalize_title("Live and Let Die") == "live and let die"


def test_normalize_title_preserves_legitimate_clean_word():
    assert normalize_title("Clean Up Woman") == "clean up woman"


def test_normalize_title_removes_trailing_version_noise():
    assert normalize_title("Song Title - Live") == "song title"
    assert normalize_title("Song Title Radio Edit") == "song title"


def test_normalize_title_removes_parenthetical_live_metadata():
    assert normalize_title("Song Title (Live at Wembley)") == "song title"


def test_normalize_album_uses_general_text_rules():
    assert normalize_album("Album Name (Deluxe Edition)") == "album name"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Ordinary Song", "studio"),
        ("Song (Live)", "live"),
        ("Song - 2011 Remastered", "remaster"),
        ("Song (Mono Mix)", "mono"),
        ("Song (Stereo Mix)", "stereo"),
        ("Song - Single Version", "single"),
        ("Song - Acoustic", "acoustic"),
        ("Song Demo", "demo"),
        ("Song Take 2", "alternate"),
        ("Song Instrumental", "instrumental"),
        ("Song Radio Edit", "radio"),
        ("Song Extended", "extended"),
    ],
)
def test_classify_version(title, expected):
    assert classify_version(title) == expected


def test_title_tokens_are_unique_sorted_and_drop_articles():
    assert title_tokens("The Sound of the Sound") == ("of", "sound")


def test_title_tokens_empty_input():
    assert title_tokens("") == ()


def test_normalize_key_is_compact_and_unicode_folded():
    assert normalize_key("Beyoncé & Jay-Z") == "beyoncejayz"


def test_canonical_artist_key_resolves_alias_and_canonical_name():
    aliases = {"Doobie Brothers": "The Doobie Brothers"}
    expected = "thedoobiebrothers"
    assert canonical_artist_key("Doobie Brothers", aliases) == expected
    assert canonical_artist_key("The Doobie Brothers", aliases) == expected


def test_canonical_artist_key_returns_original_key_when_unaliased():
    assert canonical_artist_key("Steely Dan", {}) == "steelydan"


def test_artist_lookup_names_returns_alias_family_without_duplicates():
    aliases = {
        "Doobie Brothers": "The Doobie Brothers",
        "The Doobies": "The Doobie Brothers",
    }
    names = artist_lookup_names("Doobie Brothers", aliases)
    assert set(names) == {
        "Doobie Brothers",
        "The Doobie Brothers",
        "The Doobies",
    }
    assert len(names) == 3


def test_empty_values_normalize_safely():
    assert normalize_text("") == ""
    assert normalize_artist("") == ""
    assert normalize_title("") == ""
    assert normalize_album("") == ""
    assert normalize_key("") == ""
    assert canonical_artist_key("", {}) == ""

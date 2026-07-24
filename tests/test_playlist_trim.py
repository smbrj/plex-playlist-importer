import pytest
from plex_playlist.playlist_trim import playlist_trim_preview


def test_below_limit():
    result = playlist_trim_preview(
        current_rating_keys=list(range(400)),
        requested_rating_keys=list(range(400, 450)),
        trim_limit=500,
    )
    assert result["new_unique"] == 50
    assert result["remove"] == 0
    assert result["final"] == 450


def test_update_counts_only_new_unique_tracks():
    result = playlist_trim_preview(
        current_rating_keys=[1, 2, 3],
        requested_rating_keys=[2, 3, 4, 4, 5],
        trim_limit=4,
    )
    assert result["new_unique"] == 2
    assert result["after_update"] == 5
    assert result["remove"] == 1
    assert result["final"] == 4


def test_already_oversized_is_repaired_even_without_additions():
    result = playlist_trim_preview(
        current_rating_keys=list(range(600)),
        requested_rating_keys=[],
        trim_limit=500,
    )
    assert result["remove"] == 100
    assert result["final"] == 500


def test_zero_is_unlimited():
    result = playlist_trim_preview(
        current_rating_keys=list(range(600)),
        requested_rating_keys=list(range(600, 620)),
        trim_limit=0,
    )
    assert result["remove"] == 0
    assert result["final"] == 620


def test_negative_rejected():
    with pytest.raises(ValueError):
        playlist_trim_preview(
            current_rating_keys=[],
            requested_rating_keys=[],
            trim_limit=-1,
        )

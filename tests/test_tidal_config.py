from plex_playlist.tidal_config import parse_quality_preference


def test_default_quality_preference():
    parsed = parse_quality_preference(None)
    assert parsed.values == (
        "DOLBY_ATMOS",
        "HIRES_LOSSLESS",
        "LOSSLESS",
    )


def test_config_is_case_insensitive_and_whitespace_tolerant():
    parsed = parse_quality_preference(
        " dolby_atmos, hires_lossless , lossless "
    )
    assert parsed.values == (
        "DOLBY_ATMOS",
        "HIRES_LOSSLESS",
        "LOSSLESS",
    )


def test_duplicate_values_are_ignored_preserving_first_position():
    parsed = parse_quality_preference(
        "LOSSLESS,DOLBY_ATMOS,LOSSLESS,HIRES_LOSSLESS"
    )
    assert parsed.values == (
        "LOSSLESS",
        "DOLBY_ATMOS",
        "HIRES_LOSSLESS",
    )


def test_unknown_future_tag_is_retained():
    parsed = parse_quality_preference(
        "FUTURE_FORMAT,DOLBY_ATMOS,LOSSLESS"
    )
    assert parsed.values == (
        "FUTURE_FORMAT",
        "DOLBY_ATMOS",
        "LOSSLESS",
    )


def test_commas_only_falls_back_to_default():
    parsed = parse_quality_preference(" , , ")
    assert parsed.values[0] == "DOLBY_ATMOS"
    assert parsed.warnings

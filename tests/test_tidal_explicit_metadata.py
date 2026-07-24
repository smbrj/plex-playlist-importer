import pytest

from plex_playlist.tidal_client import _parse_track_document


def payload(explicit_marker=...):
    attributes = {
        "title": "Test Song",
        "mediaTags": ["LOSSLESS"],
    }
    if explicit_marker is not ...:
        attributes["explicit"] = explicit_marker

    return {
        "data": {
            "type": "tracks",
            "id": "123",
            "attributes": attributes,
            "relationships": {},
        },
        "included": [],
    }


@pytest.mark.parametrize(
    "explicit_marker,expected",
    [
        (True, True),
        (False, False),
        (None, False),
        ("", False),
        ("true", False),
        (1, False),
    ],
)
def test_only_literal_tidal_boolean_true_is_explicit(
    explicit_marker,
    expected,
):
    parsed = _parse_track_document(
        payload(explicit_marker),
        expected_id="123",
    )
    assert parsed.explicit is expected


def test_missing_explicit_field_is_not_explicit():
    parsed = _parse_track_document(
        payload(),
        expected_id="123",
    )
    assert parsed.explicit is False

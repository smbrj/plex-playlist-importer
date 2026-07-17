from argparse import Namespace
from pathlib import Path

import pytest

from plex_playlist.xmstation_profiles import (
    XMProfileRunResult,
    XMStationProfileError,
    aggregate_profile_exit_code,
    apply_profile_to_args,
    format_profile_listing,
    get_xmstation_profile,
    load_xmstation_profiles,
)


def write_profiles(path: Path) -> None:
    path.write_text(
        """
[50s_gold]
channel = 72
playlist = default
history_hours = 168
max_tracks = 100
max_requests = 8
mode = update
lidarr_check = true
enabled = true

[custom]
channel = 26
playlist = My Vinyl
history_hours = 48
max_tracks =
max_requests = 4
mode = replace
enabled = false
""".strip(),
        encoding="utf-8",
    )


def args(**overrides):
    values = dict(input_file=None, xmstation=None, playlist=None, xmhours=None,
                  xm_max_requests=None, xm_max_tracks=None, update=False,
                  replace=False, sync=False, lidarr_check=False,
                  lidarr_search=False)
    values.update(overrides)
    return Namespace(**values)


def test_loads_profiles_and_default_playlist(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    write_profiles(path)
    gold = get_xmstation_profile(load_xmstation_profiles(path), "50S_GOLD")
    assert gold.channel == 72
    assert gold.playlist is None
    assert gold.uses_default_playlist is True
    assert gold.max_tracks == 100
    assert gold.enabled is True


def test_custom_playlist_and_blank_max_tracks(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    write_profiles(path)
    custom = get_xmstation_profile(load_xmstation_profiles(path), "custom")
    assert custom.playlist == "My Vinyl"
    assert custom.max_tracks is None
    assert custom.mode == "replace"
    assert custom.enabled is False


def test_profile_applies_defaults(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    write_profiles(path)
    profile = get_xmstation_profile(load_xmstation_profiles(path), "50s_gold")
    parsed = args()
    apply_profile_to_args(parsed, profile)
    assert parsed.xmstation == 72
    assert parsed.playlist is None
    assert parsed.xmhours == 168
    assert parsed.xm_max_tracks == 100
    assert parsed.xm_max_requests == 8
    assert parsed.update is True
    assert parsed.lidarr_check is True


def test_cli_overrides_profile(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    write_profiles(path)
    profile = get_xmstation_profile(load_xmstation_profiles(path), "custom")
    parsed = args(playlist="CLI Name", xmhours=24, xm_max_tracks=150,
                  xm_max_requests=10, update=True, lidarr_search=True)
    apply_profile_to_args(parsed, profile)
    assert parsed.xmstation == 26
    assert parsed.playlist == "CLI Name"
    assert parsed.xmhours == 24
    assert parsed.xm_max_tracks == 150
    assert parsed.xm_max_requests == 10
    assert parsed.update is True
    assert parsed.replace is False
    assert parsed.lidarr_search is True


def test_rejects_invalid_profile(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    path.write_text("[bad]\nchannel = 72\nhistory_hours = 999\n", encoding="utf-8")
    with pytest.raises(XMStationProfileError):
        load_xmstation_profiles(path)


def test_listing_marks_disabled_profiles(tmp_path: Path) -> None:
    path = tmp_path / "xmstations.ini"
    write_profiles(path)
    text = format_profile_listing(load_xmstation_profiles(path).values())
    assert "50s_gold" in text
    assert "custom" in text
    assert "Enabled      : no" in text
    assert "Playlist     : default" in text


def test_aggregate_exit_code() -> None:
    assert aggregate_profile_exit_code([XMProfileRunResult("a", 0), XMProfileRunResult("b", 0)]) == 0
    assert aggregate_profile_exit_code([XMProfileRunResult("a", 0), XMProfileRunResult("b", 2)]) == 2
    assert aggregate_profile_exit_code([XMProfileRunResult("a", 0), XMProfileRunResult("b", 4)]) == 1


def test_profile_header_is_compact() -> None:
    from plex_playlist.xmstation_profiles import (
        XMStationProfile,
        format_profile_header,
    )

    profile = XMStationProfile(
        name="classic_rewind",
        channel=25,
        playlist=None,
        history_hours=168,
        max_tracks=100,
        max_requests=8,
        mode="update",
        lidarr_check=True,
        lidarr_search=False,
        enabled=True,
    )

    assert format_profile_header(profile, 2, 3) == (
        "Profile 2/3: classic_rewind (channel 25)"
    )


def test_profile_summary_contains_aggregate_counts() -> None:
    from plex_playlist.xmstation_profiles import format_profile_summary

    text = format_profile_summary([
        XMProfileRunResult("success", 0),
        XMProfileRunResult("warning", 2),
        XMProfileRunResult("failure", 4),
    ])

    assert "XMPlaylist profile results" in text
    assert "Profiles processed : 3" in text
    assert "Successful         : 1" in text
    assert "With warnings      : 1" in text
    assert "Failed             : 1" in text

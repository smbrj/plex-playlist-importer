from __future__ import annotations

import configparser
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


class XMStationProfileError(ValueError):
    """Raised when xmstations.ini contains an invalid profile."""


@dataclass(frozen=True)
class XMStationProfile:
    name: str
    channel: int
    playlist: str | None
    history_hours: int
    max_tracks: int | None
    max_requests: int
    mode: str
    lidarr_check: bool
    lidarr_search: bool
    enabled: bool

    @property
    def uses_default_playlist(self) -> bool:
        return not self.playlist or self.playlist.casefold() == "default"


@dataclass(frozen=True)
class XMProfileRunResult:
    name: str
    returncode: int

    @property
    def status(self) -> str:
        if self.returncode == 0:
            return "SUCCESS"
        if self.returncode == 2:
            return "COMPLETED WITH WARNINGS"
        return "FAILED"


_VALID_MODES = {"create", "update", "replace", "sync"}


def _optional_positive_int(parser: configparser.ConfigParser, section: str, option: str) -> int | None:
    raw = parser.get(section, option, fallback="").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise XMStationProfileError(f"[{section}] {option} must be an integer or blank") from exc
    if value < 1:
        raise XMStationProfileError(f"[{section}] {option} must be at least 1")
    return value


def load_xmstation_profiles(path: Path) -> dict[str, XMStationProfile]:
    path = Path(path)
    if not path.exists():
        raise XMStationProfileError(f"XMPlaylist station profile file not found: {path}")
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(path, encoding="utf-8"):
        raise XMStationProfileError(f"Unable to read XMPlaylist station profile file: {path}")
    profiles: dict[str, XMStationProfile] = {}
    for section in parser.sections():
        try:
            channel = parser.getint(section, "channel")
        except (configparser.NoOptionError, ValueError) as exc:
            raise XMStationProfileError(f"[{section}] channel is required and must be an integer") from exc
        if channel < 1:
            raise XMStationProfileError(f"[{section}] channel must be at least 1")
        history_hours = parser.getint(section, "history_hours", fallback=168)
        if not 1 <= history_hours <= 720:
            raise XMStationProfileError(f"[{section}] history_hours must be between 1 and 720")
        max_requests = parser.getint(section, "max_requests", fallback=8)
        if max_requests < 2:
            raise XMStationProfileError(f"[{section}] max_requests must be at least 2")
        max_tracks = _optional_positive_int(parser, section, "max_tracks")
        mode = parser.get(section, "mode", fallback="update").strip().casefold()
        if mode not in _VALID_MODES:
            raise XMStationProfileError(f"[{section}] mode must be one of: {', '.join(sorted(_VALID_MODES))}")
        playlist_raw = parser.get(section, "playlist", fallback="default").strip()
        playlist = None if not playlist_raw or playlist_raw.casefold() == "default" else playlist_raw
        lidarr_check = parser.getboolean(section, "lidarr_check", fallback=False)
        lidarr_search = parser.getboolean(section, "lidarr_search", fallback=False)
        if lidarr_check and lidarr_search:
            raise XMStationProfileError(f"[{section}] enable only one of lidarr_check or lidarr_search")
        profile = XMStationProfile(
            name=section,
            channel=channel,
            playlist=playlist,
            history_hours=history_hours,
            max_tracks=max_tracks,
            max_requests=max_requests,
            mode=mode,
            lidarr_check=lidarr_check,
            lidarr_search=lidarr_search,
            enabled=parser.getboolean(section, "enabled", fallback=True),
        )
        profiles[section.casefold()] = profile
    if not profiles:
        raise XMStationProfileError(f"No station profiles found in {path}")
    return profiles


def get_xmstation_profile(profiles: dict[str, XMStationProfile], name: str) -> XMStationProfile:
    try:
        return profiles[name.casefold()]
    except KeyError as exc:
        available = ", ".join(sorted(profile.name for profile in profiles.values()))
        raise XMStationProfileError(f"Unknown XMPlaylist profile '{name}'. Available profiles: {available}") from exc


def apply_profile_to_args(args, profile: XMStationProfile) -> None:
    if getattr(args, "input_file", None) is not None:
        raise XMStationProfileError("--xmprofile cannot be combined with an input file")
    if getattr(args, "xmstation", None) is not None:
        raise XMStationProfileError("--xmprofile cannot be combined with --xmstation")
    args.xmstation = profile.channel
    if getattr(args, "playlist", None) is None and profile.playlist:
        args.playlist = profile.playlist
    if getattr(args, "xmhours", None) is None:
        args.xmhours = profile.history_hours
    if getattr(args, "xm_max_requests", None) is None:
        args.xm_max_requests = profile.max_requests
    if hasattr(args, "xm_max_tracks") and getattr(args, "xm_max_tracks", None) is None:
        args.xm_max_tracks = profile.max_tracks
    explicit_mode = any(bool(getattr(args, option, False)) for option in ("update", "replace", "sync"))
    if not explicit_mode:
        args.update = profile.mode == "update"
        args.replace = profile.mode == "replace"
        args.sync = profile.mode == "sync"
    if not getattr(args, "lidarr_check", False) and not getattr(args, "lidarr_search", False):
        args.lidarr_check = profile.lidarr_check
        args.lidarr_search = profile.lidarr_search


def format_profile_listing(profiles: Iterable[XMStationProfile]) -> str:
    lines = ["XMPlaylist station profiles:", ""]
    for profile in sorted(profiles, key=lambda item: item.name.casefold()):
        playlist = profile.playlist or "default"
        max_tracks = str(profile.max_tracks) if profile.max_tracks is not None else "unlimited"
        lidarr = "search" if profile.lidarr_search else "check" if profile.lidarr_check else "disabled"
        lines.extend([
            f"  {profile.name}",
            f"    Enabled      : {'yes' if profile.enabled else 'no'}",
            f"    Channel      : {profile.channel}",
            f"    Playlist     : {playlist}",
            f"    History      : {profile.history_hours} hours",
            f"    Track target : {max_tracks}",
            f"    Requests     : {profile.max_requests}",
            f"    Mode         : {profile.mode.upper()}",
            f"    Lidarr       : {lidarr}",
            "",
        ])
    return "\n".join(lines).rstrip()


def _append_option(command: list[str], flag: str, value) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def build_profile_subprocess_command(*, script_path: Path, config_path: Path, profiles_path: Path, profile: XMStationProfile, args) -> list[str]:
    command = [sys.executable, str(script_path), "--config", str(config_path), "--xmstations-file", str(profiles_path), "--xmprofile", profile.name]
    _append_option(command, "--playlist", getattr(args, "playlist", None))
    _append_option(command, "--xmhours", getattr(args, "xmhours", None))
    _append_option(command, "--xm-max-requests", getattr(args, "xm_max_requests", None))
    if hasattr(args, "xm_max_tracks"):
        _append_option(command, "--xm-max-tracks", getattr(args, "xm_max_tracks", None))
    for flag, attr in (("--dry-run", "dry_run"), ("--update", "update"), ("--replace", "replace"), ("--sync", "sync"), ("--refresh-cache", "refresh_cache"), ("--no-cache", "no_cache"), ("--lidarr-check", "lidarr_check"), ("--lidarr-search", "lidarr_search")):
        if bool(getattr(args, attr, False)):
            command.append(flag)
    return command


def run_all_profiles(*, profiles: Sequence[XMStationProfile], script_path: Path, config_path: Path, profiles_path: Path, args) -> list[XMProfileRunResult]:
    results: list[XMProfileRunResult] = []
    enabled = [profile for profile in profiles if profile.enabled]
    if not enabled:
        raise XMStationProfileError("No enabled XMPlaylist station profiles were found")
    for index, profile in enumerate(enabled, start=1):
        print(f"\n=== XMPlaylist profile {index}/{len(enabled)}: {profile.name} (channel {profile.channel}) ===", flush=True)
        command = build_profile_subprocess_command(script_path=script_path, config_path=config_path, profiles_path=profiles_path, profile=profile, args=args)
        completed = subprocess.run(command, check=False)
        results.append(XMProfileRunResult(name=profile.name, returncode=completed.returncode))
    print("\nXMPlaylist profile summary:")
    for result in results:
        print(f"  {result.name:<24} {result.status:<24} exit={result.returncode}")
    print(f"\nProfiles processed : {len(results)}\nSuccessful         : {sum(r.returncode == 0 for r in results)}\nWith warnings      : {sum(r.returncode == 2 for r in results)}\nFailed             : {sum(r.returncode not in (0, 2) for r in results)}")
    return results


def aggregate_profile_exit_code(results: Sequence[XMProfileRunResult]) -> int:
    if any(result.returncode not in (0, 2) for result in results):
        return 1
    if any(result.returncode == 2 for result in results):
        return 2
    return 0

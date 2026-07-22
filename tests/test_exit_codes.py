from types import SimpleNamespace
import configparser
import sys

import pytest

import playlist_import_v2 as app
from plex_playlist.models import PlaylistMode
from plex_playlist.runtime import ComponentHealth


class FakeCache:
    def __init__(self, database):
        self.database = database

    def initialize(self):
        return None


class FakePlex:
    next_health = ComponentHealth.available_health("ok")
    next_tracks = []
    next_stale = []
    instances = []

    def __init__(self, url, token, library_name):
        self.updated = False
        self.update_args = None
        FakePlex.instances.append(self)

    def is_available(self):
        return FakePlex.next_health

    def resolve_matches(self, results):
        return SimpleNamespace(
            tracks=list(FakePlex.next_tracks),
            stale_matches=list(FakePlex.next_stale),
        )

    def update_playlist(self, *, name, tracks, mode):
        self.updated = True
        self.update_args = (name, tracks, mode)


def minimal_config():
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "application": {"config_version": "3"},
        "plex": {
            "url": "http://plex",
            "token": "token",
            "library": "Music",
        },
        "cache": {
            "database": "cache/test.db",
            "max_age_hours": "24",
        },
        "reports": {"include_file_paths": "false"},
        "matching": {},
        "logging": {},
        "analytics": {"enabled": "false"},
        "alias_intelligence": {},
    })
    return cfg


@pytest.fixture(autouse=True)
def isolate_main(monkeypatch):
    FakePlex.instances.clear()
    FakePlex.next_health = ComponentHealth.available_health("ok")
    FakePlex.next_tracks = []
    FakePlex.next_stale = []

    monkeypatch.setattr(app, "load_config", lambda path: minimal_config())
    monkeypatch.setattr(
        app,
        "configure_logging",
        lambda cfg, path: app.logger,
    )
    monkeypatch.setattr(
        app,
        "build_matching_config",
        lambda cfg, path: SimpleNamespace(artist_aliases={}),
    )
    monkeypatch.setattr(app, "LibraryCache", FakeCache)
    monkeypatch.setattr(
        app,
        "run_library_intelligence",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(app, "PlexClient", FakePlex)
    monkeypatch.setattr(
        app,
        "load_search_index",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        app,
        "load_input_source",
        lambda **kwargs: ([], "Test Playlist"),
    )
    monkeypatch.setattr(app, "generate_reports", lambda **kwargs: None)
    monkeypatch.setattr(
        app,
        "record_alias_effectiveness",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        app,
        "write_run_analytics",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        app,
        "log_run_summary",
        lambda status: None,
    )
    monkeypatch.setattr(
        app,
        "run_lidarr_diagnostics",
        lambda **kwargs: [],
    )

    def startup(**kwargs):
        status = kwargs["run_status"]
        status.plex = FakePlex.next_health
        return None, None

    monkeypatch.setattr(app, "run_startup_health_checks", startup)

    monkeypatch.setattr(
        app,
        "run_matcher_entries",
        lambda **kwargs: SimpleNamespace(results=[]),
    )


def run_main(monkeypatch, *args):
    monkeypatch.setattr(
        sys,
        "argv",
        ["playlist_import_v2.py", "input.csv", *args],
    )
    return app.main()


def test_normal_success_returns_normally_and_updates_playlist(monkeypatch):
    assert run_main(monkeypatch) is None
    assert FakePlex.instances[-1].updated is True


def test_clean_dry_run_returns_normally(monkeypatch):
    assert run_main(monkeypatch, "--dry-run") is None
    assert FakePlex.instances[-1].updated is False


def test_dry_run_with_warning_exits_2(monkeypatch):
    def startup(**kwargs):
        status = kwargs["run_status"]
        status.plex = ComponentHealth.available_health("ok")
        status.warnings.append("degraded component")
        return None, None

    monkeypatch.setattr(app, "run_startup_health_checks", startup)

    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, "--dry-run")

    assert exc.value.code == 2


def test_argparse_usage_error_also_uses_standard_exit_2():
    parser = app.build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args([
            "input.csv",
            "--update",
            "--replace",
        ])

    assert exc.value.code == 2


def test_plex_unavailable_skips_playlist_and_exits_4(monkeypatch):
    FakePlex.next_health = ComponentHealth.unavailable("offline")

    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch)

    assert exc.value.code == 4
    assert FakePlex.instances[-1].updated is False


def one_matched_session(**kwargs):
    return SimpleNamespace(
        results=[SimpleNamespace(matched=object())],
    )


@pytest.mark.parametrize("mode_flag", ["--replace", "--sync"])
def test_stale_cached_match_blocks_destructive_modes_with_exit_5(
    monkeypatch,
    mode_flag,
):
    monkeypatch.setattr(
        app,
        "run_matcher_entries",
        one_matched_session,
    )
    FakePlex.next_tracks = []
    FakePlex.next_stale = [object()]

    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch, mode_flag)

    assert exc.value.code == 5
    assert FakePlex.instances[-1].updated is False


def test_stale_cached_match_allows_update_to_continue(monkeypatch):
    monkeypatch.setattr(
        app,
        "run_matcher_entries",
        one_matched_session,
    )
    FakePlex.next_tracks = []
    FakePlex.next_stale = [object()]

    assert run_main(monkeypatch, "--update") is None
    assert FakePlex.instances[-1].updated is True
    assert FakePlex.instances[-1].update_args[2] is PlaylistMode.UPDATE


def test_resolution_count_mismatch_exits_5(monkeypatch):
    monkeypatch.setattr(
        app,
        "run_matcher_entries",
        one_matched_session,
    )
    FakePlex.next_tracks = []
    FakePlex.next_stale = []

    with pytest.raises(SystemExit) as exc:
        run_main(monkeypatch)

    assert exc.value.code == 5
    assert FakePlex.instances[-1].updated is False


def test_cli_keyboard_interrupt_exits_1(monkeypatch):
    def interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(app, "main", interrupt)

    with pytest.raises(SystemExit) as exc:
        app.cli()

    assert exc.value.code == 1

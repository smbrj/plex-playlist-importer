from __future__ import annotations

import configparser
import logging
import sys
import types
from pathlib import Path

import pytest

# The ChatGPT validation container does not include plexapi. The real project
# does; these stubs only allow importing the orchestrator for unit testing here.
try:
    import plexapi  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    plexapi_pkg = types.ModuleType("plexapi")
    plexapi_server = types.ModuleType("plexapi.server")
    plexapi_exceptions = types.ModuleType("plexapi.exceptions")

    class PlexServer:  # pragma: no cover - validation-container shim
        pass

    class NotFound(Exception):  # pragma: no cover - validation-container shim
        pass

    plexapi_server.PlexServer = PlexServer
    plexapi_exceptions.NotFound = NotFound
    sys.modules["plexapi"] = plexapi_pkg
    sys.modules["plexapi.server"] = plexapi_server
    sys.modules["plexapi.exceptions"] = plexapi_exceptions

import playlist_import_v2 as app
from plex_playlist.logging_config import setup_logging
from plex_playlist.models import MatchingConfig, MatchingSession
from plex_playlist.reporting import write_unmatched_csv
from plex_playlist.runtime import ComponentHealth


def _base_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict(
        {
            "application": {"config_version": "3"},
            "matching": {},
            "logging": {},
            "artist_aliases": {"enabled": "false"},
            "reports": {},
            "lidarr": {
                "enabled": "true",
                "url": "http://lidarr",
                "api_key": "secret",
                "timeout_seconds": "20",
                "remember_failed_searches": "true",
                "retry_search_after_days": "7",
                "search_history_database": "cache/lidarr_search_history.db",
            },
        }
    )
    return cfg


def test_matching_config_defaults_are_not_reversed(tmp_path: Path) -> None:
    cfg = _base_config()
    built = app.build_matching_config(cfg, tmp_path / "config.ini")

    assert built.min_title_score == 95
    assert built.fallback_title_score == 80
    assert MatchingConfig().min_title_score == 95
    assert MatchingConfig().fallback_title_score == 80


def test_load_config_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "config.ini"
    path.write_text("[application]\nconfig_version = 2\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Unsupported configuration version 2"):
        app.load_config(path)


def test_report_paths_use_config_directory(tmp_path: Path) -> None:
    cfg = _base_config()
    cfg["reports"] = {
        "directory": "reports",
        "match": "playlist_report.csv",
        "unmatched": "unmatched.csv",
        "lidarr": "lidarr.csv",
    }
    config_path = tmp_path / "config.ini"

    assert app.resolve_report_path(
        cfg, config_path, key="match", fallback_filename="fallback.csv"
    ) == tmp_path / "reports" / "playlist_report.csv"
    assert app.resolve_report_path(
        cfg, config_path, key="lidarr", fallback_filename="fallback.csv"
    ) == tmp_path / "reports" / "lidarr.csv"


def test_configure_logging_passes_configured_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    cfg["logging"] = {
        "level": "WARNING",
        "directory": "var/logs",
        "filename": "importer-main.log",
    }
    captured = {}

    def fake_setup_logging(**kwargs):
        captured.update(kwargs)
        return logging.getLogger("test")

    monkeypatch.setattr(app, "setup_logging", fake_setup_logging)
    app.configure_logging(cfg, tmp_path / "config.ini")

    assert captured == {
        "level": "WARNING",
        "directory": tmp_path / "var" / "logs",
        "filename": "importer-main.log",
    }


def test_setup_logging_honors_directory_and_filename(tmp_path: Path) -> None:
    logger = logging.getLogger("plex_playlist")
    old_handlers = list(logger.handlers)
    for handler in old_handlers:
        logger.removeHandler(handler)
        handler.close()

    try:
        configured = setup_logging(
            level="ERROR",
            directory=tmp_path / "logs",
            filename="custom.log",
        )
        assert (tmp_path / "logs" / "custom.log").exists()
        assert (tmp_path / "logs" / "debug.log").exists()
        assert (tmp_path / "logs" / "runs").is_dir()
        console = next(
            handler for handler in configured.handlers
            if type(handler) is logging.StreamHandler
        )
        assert console.level == logging.ERROR
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        for handler in old_handlers:
            logger.addHandler(handler)


def test_lidarr_client_uses_20_second_timeout() -> None:
    cfg = _base_config()
    client = app.build_lidarr_client(cfg)
    assert client is not None
    assert client.timeout_seconds == 20


def test_lidarr_runtime_wires_history_and_retry_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    captured = {}

    class FakeClient:
        def is_available(self):
            return ComponentHealth.available_health("test Lidarr")

    def fake_build_lidarr_diagnostics(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(app, "build_lidarr_diagnostics", fake_build_lidarr_diagnostics)
    monkeypatch.setattr(app, "write_lidarr_diagnostic_csv", lambda *a, **k: None)
    monkeypatch.setattr(app, "log_lidarr_summary", lambda rows: None)

    app.run_lidarr_diagnostics(
        cfg=cfg,
        session=MatchingSession(),
        output_path=tmp_path / "lidarr.csv",
        search_missing_albums=True,
        client=FakeClient(),
        config_path=tmp_path / "config.ini",
    )

    assert captured["remember_searches"] is True
    assert captured["retry_after_days"] == 7.0
    assert captured["history_store"].database == (
        tmp_path / "cache" / "lidarr_search_history.db"
    )



def test_lidarr_history_can_be_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _base_config()
    cfg["lidarr"]["remember_failed_searches"] = "false"
    captured = {}

    class FakeClient:
        def is_available(self):
            return ComponentHealth.available_health("test Lidarr")

    def fake_build_lidarr_diagnostics(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(app, "build_lidarr_diagnostics", fake_build_lidarr_diagnostics)
    monkeypatch.setattr(app, "write_lidarr_diagnostic_csv", lambda *a, **k: None)
    monkeypatch.setattr(app, "log_lidarr_summary", lambda rows: None)

    app.run_lidarr_diagnostics(
        cfg=cfg,
        session=MatchingSession(),
        output_path=tmp_path / "lidarr.csv",
        client=FakeClient(),
        config_path=tmp_path / "config.ini",
    )

    assert captured["remember_searches"] is False
    assert captured["history_store"] is None

def test_unmatched_writer_creates_parent_directory(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "unmatched.csv"
    write_unmatched_csv(MatchingSession(), output)
    assert output.exists()

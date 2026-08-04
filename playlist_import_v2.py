#!/usr/bin/env python3
"""
V2 CLI Orchestrator

Wires together:
- cache
- plex client
- matcher
- reporting

No business logic lives here.
"""

from __future__ import annotations

import argparse
import json
import glob
import configparser
import logging
import sys
from time import perf_counter
from pathlib import Path

from plex_playlist.cache import LibraryCache
from plex_playlist.runtime import (
    RunStatus,
    ComponentHealth,
    HealthState,
)
from plex_playlist.plex_client import PlexClient
from plex_playlist.parser import parse_playlist_file
from plex_playlist.matcher import match_playlist
from plex_playlist.logging_config import setup_logging

#  used for the no-cache option to force a refresh of the library from Plex
from plex_playlist.search_index import SearchIndex
#

from plex_playlist.models import (
    MatchingConfig,
    MatchingSession,
    PlaylistMode,
)

from plex_playlist.reporting import write_duplicates_csv

from plex_playlist.reporting import (
    count_metadata_warnings,
    log_match_summary,
    write_match_report_csv,
    write_unmatched_csv,
)

from plex_playlist.resources import load_artist_aliases
from plex_playlist.alias_usage import (
    AliasUsageStore,
    count_alias_usage,
)
from plex_playlist.analytics import RunAnalytics, append_match_analytics_csv, count_lidarr_states, write_latest_run_json
from plex_playlist.alias_intelligence import (
    audit_aliases_csv,
    export_plex_artists_csv,
    import_approved_aliases,
    suggest_aliases_csv,
)
from plex_playlist.lidarr_client import LidarrClient
from plex_playlist.lidarr_search_history import LidarrSearchHistoryStore
from plex_playlist.xmplaylist_client import XMPlaylistClient
from plex_playlist.xmplaylist_source import ingest_station
from plex_playlist.xmstation_profiles import (
    XMStationProfileError,
    aggregate_profile_exit_code,
    apply_profile_to_args,
    format_profile_listing,
    get_xmstation_profile,
    load_xmstation_profiles,
    run_all_profiles,
)
from plex_playlist.xmplaylist_state import XMPlaylistStateStore
from plex_playlist.tidal_client import TidalClient, TidalError
from plex_playlist.tidal_matcher import qualifying_candidates
from plex_playlist.tidal_diagnostics import format_tidal_search_results
from plex_playlist.tidal_cache import TidalSearchCache
from plex_playlist.tidal_service import TidalSearchService
from plex_playlist.tidal_reporting import (
    build_tidal_unmatched_rows,
    write_tidal_matched_report,
    write_tidal_unmatched_report,
)
from plex_playlist.tidal_config import parse_quality_preference
from plex_playlist.rejected_terms import parse_rejected_terms
from plex_playlist.tidal_user_auth import (
    TidalTokenStore,
    TidalUserTokenProvider,
    WRITE_SCOPES,
    authorize_interactively,
)
from plex_playlist.tidal_account import TidalAccountClient
from plex_playlist.tidal_companion import TidalCompanionPlaylistService
from plex_playlist.tidal_state import TidalStateStore
from plex_playlist.tidal_reconcile import TidalReconciliationPlanner, TidalReconcileAction, TidalReconciliationExecutor
from plex_playlist.playlist_trim import (
    playlist_trim_preview,
    filter_tidal_reconciliation_for_final_plex_membership,
)

from plex_playlist.lidarr_reporting import (
    LidarrDiagnosticRow,
    build_lidarr_diagnostics,
    count_unique_unmatched_artists,
    format_lidarr_summary,
    summarize_lidarr_diagnostics,
    write_lidarr_diagnostic_csv,
)

#
#  define logging
#

logger = logging.getLogger("plex_playlist")

# ============================================================
# Config
# ============================================================

SUPPORTED_CONFIG_VERSION = 3


def load_config(path: Path) -> configparser.ConfigParser:
    """Load and validate the application configuration file."""

    cfg = configparser.ConfigParser()
    loaded = cfg.read(path)
    if not loaded:
        raise RuntimeError(f"Configuration file not found: {path}")

    version = cfg.getint(
        "application",
        "config_version",
        fallback=0,
    )
    if version != SUPPORTED_CONFIG_VERSION:
        raise RuntimeError(
            "Unsupported configuration version "
            f"{version}; expected {SUPPORTED_CONFIG_VERSION}."
        )

    return cfg


def resolve_config_path(config_path: Path, value: str | Path) -> Path:
    """Resolve a configured path relative to the config file."""

    path = Path(value)
    if path.is_absolute():
        return path
    return config_path.resolve().parent / path


def configure_logging(
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> logging.Logger:
    """Initialize logging from the [logging] configuration section."""

    level = cfg.get("logging", "level", fallback="INFO").strip() or "INFO"
    directory = resolve_config_path(
        config_path,
        cfg.get("logging", "directory", fallback="logs"),
    )
    filename = cfg.get(
        "logging",
        "filename",
        fallback="playlist_import.log",
    ).strip() or "playlist_import.log"
    return setup_logging(
        level=level,
        directory=directory,
        filename=filename,
    )


def resolve_report_path(
    cfg: configparser.ConfigParser,
    config_path: Path,
    *,
    key: str,
    fallback_filename: str,
) -> Path:
    """Resolve one configured report path using [reports] directory."""

    configured = cfg.get("reports", key, fallback=fallback_filename).strip()
    value = Path(configured or fallback_filename)
    if value.is_absolute():
        return value

    directory = Path(
        cfg.get("reports", "directory", fallback="reports").strip()
        or "reports"
    )
    combined = value if value.parent != Path('.') else directory / value
    return resolve_config_path(config_path, combined)


def build_matching_config(
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> MatchingConfig:
    match_cfg = cfg["matching"]
    logging_cfg = cfg["logging"]

    artist_aliases: dict[str, str] = {}

    aliases_enabled = cfg.getboolean(
        "artist_aliases",
        "enabled",
        fallback=True,
    )

    if aliases_enabled:
        configured_alias_path = Path(
            cfg.get(
                "artist_aliases",
                "file",
                fallback="resources/aliases.txt",
            )
        )

        if configured_alias_path.is_absolute():
            alias_path = configured_alias_path
        else:
            alias_path = (
                config_path.resolve().parent
                / configured_alias_path
            )

        artist_aliases = load_artist_aliases(alias_path)
    else:
        logger.info("Artist aliases disabled")


    preferred_versions = [
        value.strip().lower()
        for value in match_cfg.get(
            "preferred_versions",
            "studio,remaster,mono,stereo,single,album,live,acoustic,demo,alternate,instrumental,radio,extended,edit",
        ).split(",")
        if value.strip()
    ]
    rejected_terms = parse_rejected_terms(
        match_cfg.get("rejected_terms", fallback="")
    )
    normalized_preferred = set(parse_rejected_terms(preferred_versions))
    overlap = sorted(normalized_preferred.intersection(rejected_terms))
    if overlap:
        logger.warning(
            "Matching configuration overlap: %s appear in both "
            "preferred_versions and rejected_terms; rejected_terms "
            "takes precedence",
            ", ".join(repr(value) for value in overlap),
        )

    return MatchingConfig(
        threshold=match_cfg.getfloat("threshold", 85),
        workers=match_cfg.getint("threads", 8),
        artist_weight=match_cfg.getfloat("artist_weight", 0.25),
        album_artist_weight=match_cfg.getfloat("album_artist_weight", 0.15),
        title_weight=match_cfg.getfloat("title_weight", 0.45),
        combined_weight=match_cfg.getfloat("combined_weight", 0.15),
        preferred_versions=preferred_versions,
        rejected_terms=rejected_terms,
        min_title_score=match_cfg.getfloat("min_title_score", 95),
        fallback_title_score=match_cfg.getfloat("fallback_title_score", 80),
        debug=logging_cfg.getboolean("debug", False),
        trace=logging_cfg.getboolean("trace", False),
        artist_aliases=artist_aliases,
    )


def get_playlist_mode(args) -> PlaylistMode:
    if args.update:
        return PlaylistMode.UPDATE

    if args.replace:
        return PlaylistMode.REPLACE

    if args.sync:
        return PlaylistMode.SYNC

    return PlaylistMode.CREATE

def build_xmplaylist_client(
    cfg: configparser.ConfigParser,
) -> XMPlaylistClient:
    return XMPlaylistClient(
        base_url=cfg.get(
            "xmplaylist",
            "base_url",
            fallback="https://xmplaylist.com",
        ).strip(),
        timeout_seconds=cfg.getfloat(
            "xmplaylist",
            "timeout_seconds",
            fallback=20.0,
        ),
        user_agent=cfg.get(
            "xmplaylist",
            "user_agent",
            fallback="plex-playlist-importer/1.0",
        ).strip(),
    )


def build_lidarr_client(
    cfg: configparser.ConfigParser,
) -> LidarrClient | None:
    if not cfg.has_section("lidarr"):
        return None

    if not cfg.getboolean("lidarr", "enabled", fallback=False):
        return None

    url = cfg.get("lidarr", "url", fallback="").strip()
    api_key = cfg.get("lidarr", "api_key", fallback="").strip()
    if not url or not api_key:
        return None

    return LidarrClient(
        url=url,
        api_key=api_key,
        timeout_seconds=cfg.getfloat(
            "lidarr",
            "timeout_seconds",
            fallback=20.0,
        ),
    )


def run_startup_health_checks(
    *,
    args,
    cfg: configparser.ConfigParser,
    cache: LibraryCache,
    plex: PlexClient,
    run_status: RunStatus,
) -> tuple[XMPlaylistClient | None, LidarrClient | None]:
    """Build a reusable snapshot of dependency health."""

    try:
        count = cache.track_count()
        age = cache.cache_age_hours()
        run_status.cache_track_count = count
        run_status.cache_age_hours = age
        run_status.cache_state = (
            "EMPTY"
            if count == 0
            else (
                "STALE"
                if cache.is_stale(
                    cfg.getfloat(
                        "cache",
                        "max_age_hours",
                        fallback=24.0,
                    )
                )
                else "FRESH"
            )
        )
        run_status.cache = ComponentHealth.available_health(
            f"{count} tracks; state={run_status.cache_state}"
        )
    except Exception as exc:
        run_status.cache = ComponentHealth.unavailable(str(exc))

    run_status.plex = plex.is_available()

    xm_client: XMPlaylistClient | None = None
    if args.xmstation is not None:
        try:
            xm_client = build_xmplaylist_client(cfg)
            run_status.xmplaylist = xm_client.is_available()
        except Exception as exc:
            run_status.xmplaylist = ComponentHealth.unavailable(str(exc))
    else:
        run_status.xmplaylist = ComponentHealth.not_required(
            "file input selected"
        )

    lidarr_client = build_lidarr_client(cfg)
    if lidarr_client is None:
        if cfg.has_section("lidarr") and not cfg.getboolean(
            "lidarr",
            "enabled",
            fallback=False,
        ):
            run_status.lidarr = ComponentHealth.disabled()
        elif args.lidarr_check or args.lidarr_search:
            run_status.lidarr = ComponentHealth.unavailable(
                "enabled Lidarr configuration is incomplete"
            )
        else:
            run_status.lidarr = ComponentHealth.not_required()
    else:
        run_status.lidarr = lidarr_client.is_available()

    if cfg.has_section("tidal") and cfg.getboolean(
        "tidal",
        "enabled",
        fallback=False,
    ):
        run_status.tidal = ComponentHealth.not_configured(
            "client not implemented"
        )
    else:
        run_status.tidal = ComponentHealth.not_configured()

    return xm_client, lidarr_client


def load_search_index(*, cache: LibraryCache, plex: PlexClient, use_cache: bool, refresh_cache: bool, max_age_hours: float, run_status: RunStatus):
    """Load the searchable library with stale-cache fallback."""
    if not use_cache:
        health = run_status.plex
        if not health.available:
            health = plex.is_available()
            run_status.plex = health
        if not health.available:
            raise RuntimeError(f"Plex is unavailable and --no-cache was requested: {health.detail}")
        return SearchIndex.build(plex.load_library())

    track_count = cache.track_count()
    age_hours = cache.cache_age_hours()
    stale = cache.is_stale(max_age_hours) if track_count else True

    run_status.cache_track_count = track_count
    run_status.cache_age_hours = age_hours
    run_status.cache_state = "EMPTY" if track_count == 0 else ("STALE" if stale else "FRESH")

    if age_hours is None:
        logger.info("Plex cache: %d tracks; age unknown; status=%s", track_count, run_status.cache_state)
    else:
        logger.info("Plex cache: %d tracks; age %.2f hours; status=%s", track_count, age_hours, run_status.cache_state)

    refresh_needed = refresh_cache or track_count == 0 or stale
    if refresh_needed:
        health = run_status.plex
        if not health.available:
            health = plex.is_available()
            run_status.plex = health
        if health.available:
            logger.info("Refreshing cache from Plex")
            cache.record_refresh_attempt(result="started")
            try:
                library_tracks = plex.load_library()
                cache.replace_tracks(library_tracks)
                run_status.cache_refreshed = True
                run_status.cache_state = "FRESH"
                run_status.cache_track_count = len(library_tracks)
                run_status.cache_age_hours = 0.0
            except Exception as exc:
                cache.record_refresh_attempt(result="failed", detail=str(exc))
                if track_count == 0:
                    raise
                warning = f"Plex cache refresh failed; continuing with stale cache: {exc}"
                logger.warning(warning)
                run_status.warnings.append(warning)
        else:
            if track_count == 0:
                raise RuntimeError(f"Plex is unavailable and no usable cache exists: {health.detail}")
            warning = f"Plex unavailable; continuing with stale cache: {health.detail}"
            logger.warning(warning)
            run_status.warnings.append(warning)
    else:
        logger.info(
            "Fresh Plex cache used; startup Plex health remains %s",
            run_status.plex.state.value,
        )

    logger.info("Loading search index")
    return cache.load_index()


def run_matcher(
    *,
    playlist_file: Path,
    index: SearchIndex,
    config: MatchingConfig,
) -> MatchingSession:
    """Parse a playlist file and run the matcher."""

    entries = parse_playlist_file(playlist_file)
    return run_matcher_entries(
        entries=entries,
        index=index,
        config=config,
    )


def run_matcher_entries(
    *,
    entries,
    index: SearchIndex,
    config: MatchingConfig,
) -> MatchingSession:
    """Run the matcher for entries supplied by any input source."""

    logger.info("Playlist loaded: %d entries", len(entries))
    logger.info("Running match_playlist...")

    return match_playlist(
        playlist=entries,
        index=index,
        config=config,
    )

def generate_reports(
    *,
    session: MatchingSession,
    unmatched_path: Path,
    report_path: Path,
    artist_aliases: dict[str, str],
    include_file_paths: bool = False,
) -> None:
    """
    Generate match, unmatched, and summary reports.
    """

    log_match_summary(
        session,
        artist_aliases,
    )

    write_unmatched_csv(
        session,
        unmatched_path,
    )

    write_match_report_csv(
        report_path,
        session,
        artist_aliases,
        include_file_paths=include_file_paths,
    )

    warnings = count_metadata_warnings(
        session,
        artist_aliases,
    )

    if warnings:
        logger.info(
            "Review '%s' for metadata details.",
            report_path.name,
        )

def run_dedupe_report(
    *,
    cache: LibraryCache,
    output_path: Path,
) -> None:
    """
    Generate a duplicate logical track report from the cached library.
    """

    logger.info("Generating duplicate library report")

    tracks = cache.load_tracks()

    write_duplicates_csv(
        tracks,
        output_path,
    )

    logger.info("Duplicate report written: %s", output_path)


# ============================================================
# Build arg parser
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    CREATE is the default playlist mode. UPDATE, REPLACE, and SYNC
    are mutually exclusive.
    """

    parser = argparse.ArgumentParser(
        description="Plex Playlist Importer V3",
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        help="Playlist input file (omit when using --xmstation)",
    )

    parser.add_argument(
        "--playlist",
        help=(
            "Plex playlist name. In XMPlaylist mode, defaults to "
            "'Ch <number> - <station name>'."
        ),
    )

    parser.add_argument(
        "--xmprofile",
        help="Run one station profile from resources/xmstations.ini",
    )

    parser.add_argument(
        "--all-xmprofiles",
        action="store_true",
        help="Run every enabled XMPlaylist station profile independently",
    )

    parser.add_argument(
        "--list-xmprofiles",
        action="store_true",
        help="List XMPlaylist station profiles and exit",
    )

    parser.add_argument(
        "--xmstations-file",
        type=Path,
        default=Path("resources/xmstations.ini"),
        help="XMPlaylist station profile INI file",
    )

    parser.add_argument(
        "--xmstation",
        type=int,
        help=(
            "XMPlaylist SiriusXM channel number. Mutually exclusive "
            "with the positional input file."
        ),
    )

    parser.add_argument(
        "--xmhours",
        type=int,
        default=None,
        help=(
            "XMPlaylist history window in hours (1-720). "
            "Defaults to [xmplaylist] history_hours or 8."
        ),
    )

    parser.add_argument(
        "--xm-max-requests",
        type=int,
        default=None,
        help=(
            "Maximum XMPlaylist API requests per run, including station "
            "resolution. Defaults to [xmplaylist] max_requests_per_run or 10."
        ),
    )

    parser.add_argument(
        "--xm-max-tracks",
        type=int,
        default=None,
        help=(
            "Target number of unique XMPlaylist tracks to collect during "
            "this execution. The importer follows history pages until the "
            "target, history boundary, or request budget is reached. "
            "Defaults to [xmplaylist] max_tracks_per_run when configured; "
            "otherwise existing unlimited behavior is preserved."
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.ini"),
        help="Configuration file",
    )

    parser.add_argument(
        "--tidal-search",
        nargs=2,
        metavar=("ARTIST", "TRACK"),
        help=(
            "Read-only TIDAL diagnostic search. Loads credentials from "
            "[tidal] in config.ini, prints candidates and strict-match "
            "acceptance, and exits without modifying Plex or TIDAL."
        ),
    )


    parser.add_argument(
        "--tidal-authorize",
        action="store_true",
        help=(
            "Authorize PPI for read-only TIDAL user playlists/favorites using "
            "Authorization Code + PKCE."
        ),
    )

    parser.add_argument(
        "--tidal-authorize-write",
        action="store_true",
        help=(
            "Reauthorize PPI with TIDAL playlist/collection write scopes. "
            "This only grants permission; it does not modify account data."
        ),
    )

    parser.add_argument(
        "--tidal-write-test",
        action="store_true",
        help=(
            "Reversible TIDAL write diagnostic: create, verify, and delete "
            "one temporary playlist."
        ),
    )

    parser.add_argument(
        "--tidal-favorite-cleanup",
        action="store_true",
        help=(
            "Remove only the temporary Peg favorite left by an interrupted "
            "reversible favorite diagnostic."
        ),
    )

    parser.add_argument(
        "--tidal-favorite-test",
        action="store_true",
        help=(
            "Reversible TIDAL favorite diagnostic using Steely Dan - Peg: "
            "verify absent, add, verify present, remove, verify absent."
        ),
    )

    parser.add_argument(
        "--tidal-account-test",
        action="store_true",
        help=(
            "Read-only TIDAL account diagnostic using saved user tokens."
        ),
    )

    parser.add_argument(
        "--trim",
        type=int,
        default=None,
        help=(
            "Maximum final Plex playlist track count using FIFO trimming; "
            "0 disables trimming. Overrides [playlist] trim."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Match tracks and generate reports without changing Plex",
    )

    playlist_mode_group = (
        parser.add_mutually_exclusive_group()
    )

    playlist_mode_group.add_argument(
        "--update",
        action="store_true",
        help=(
            "Add requested tracks that are not already "
            "present in the playlist"
        ),
    )

    playlist_mode_group.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Remove the existing playlist contents and "
            "replace them with the requested tracks"
        ),
    )

    playlist_mode_group.add_argument(
        "--sync",
        action="store_true",
        help=(
            "Synchronize the Plex playlist according to the "
            "configured Plex playlist implementation"
        ),
    )

    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Refresh the SQLite library cache from Plex",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Load the library directly from Plex",
    )

    parser.add_argument(
        "--unmatched",
        type=Path,
        default=None,
        help="Unmatched-track CSV output path (overrides [reports] unmatched)",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Full match-report CSV output path (overrides [reports] match)",
    )

    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Generate a duplicate-library report and exit",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("duplicates.csv"),
        help="Duplicate-report CSV output path",
    )

    parser.add_argument(
    "--lidarr-check",
    action="store_true",
        help=(
            "Check Plex-unmatched entries against Lidarr "
            "and write a read-only diagnostic report"
        ),
    )

    parser.add_argument(
        "--lidarr-report",
        type=Path,
        default=None,
        help="Lidarr diagnostic CSV output path (overrides [reports] lidarr)",
    )

    parser.add_argument(
        "--lidarr-search",
        action="store_true",
        help=(
            "Check Plex-unmatched tracks in Lidarr and queue an "
            "album search when the matching track is known but its "
            "file is missing"
        ),
    )


    intelligence = parser.add_argument_group(
        "Library Intelligence"
    )
    intelligence.add_argument(
        "--export-artists",
        action="store_true",
        help="Export distinct Plex artists from the cache to CSV",
    )
    intelligence.add_argument(
        "--artists-output",
        type=Path,
        default=Path("reports/plex_artists.csv"),
        help="Artist inventory CSV output path",
    )
    intelligence.add_argument(
        "--suggest-aliases",
        nargs="*",
        metavar="CSV_OR_GLOB",
        default=None,
        help=(
            "Generate alias suggestions from the configured unmatched CSV, "
            "or from one or more explicit CSV paths/glob patterns"
        ),
    )
    intelligence.add_argument(
        "--alias-suggestions-output",
        type=Path,
        default=Path("reports/aliases_suggested.csv"),
        help="Alias suggestions CSV output path",
    )
    intelligence.add_argument(
        "--import-aliases",
        type=Path,
        help="Import rows marked ADD from an alias suggestions CSV",
    )
    intelligence.add_argument(
        "--audit-aliases",
        action="store_true",
        help="Write alias target and usage audit CSV",
    )
    intelligence.add_argument(
        "--alias-audit-output",
        type=Path,
        default=Path("reports/alias_audit.csv"),
        help="Alias audit CSV output path",
    )
    return parser

def load_input_source(
    *,
    args,
    cfg: configparser.ConfigParser,
    xm_client: XMPlaylistClient | None = None,
):
    """
    Return playlist entries and the target Plex playlist name.

    Exactly one source must be supplied: a positional playlist file or
    ``--xmstation``.
    """

    using_file = args.input_file is not None
    using_xmplaylist = args.xmstation is not None

    if using_file == using_xmplaylist:
        raise RuntimeError(
            "Provide exactly one input source: either an input file "
            "or --xmstation."
        )

    if using_file:
        if not args.playlist:
            raise RuntimeError(
                "--playlist is required when using an input file."
            )

        entries = parse_playlist_file(args.input_file)
        return entries, args.playlist

    history_hours = (
        args.xmhours
        if args.xmhours is not None
        else cfg.getint(
            "xmplaylist",
            "history_hours",
            fallback=8,
        )
    )

    max_requests = (
        args.xm_max_requests
        if args.xm_max_requests is not None
        else cfg.getint(
            "xmplaylist",
            "max_requests_per_run",
            fallback=10,
        )
    )

    max_tracks = args.xm_max_tracks
    if max_tracks is None:
        configured_max_tracks = cfg.get(
            "xmplaylist",
            "max_tracks_per_run",
            fallback="",
        ).strip()
        max_tracks = (
            int(configured_max_tracks)
            if configured_max_tracks
            else None
        )

    if not 1 <= history_hours <= 720:
        raise RuntimeError(
            "XMPlaylist history hours must be between 1 and 720."
        )

    if max_requests < 2:
        raise RuntimeError(
            "XMPlaylist max requests per run must be at least 2."
        )


    if max_tracks is not None and max_tracks < 1:
        raise RuntimeError(
            "XMPlaylist max tracks per run must be at least 1."
        )

    base_url = cfg.get(
        "xmplaylist",
        "base_url",
        fallback="https://xmplaylist.com",
    ).strip()

    timeout_seconds = cfg.getfloat(
        "xmplaylist",
        "timeout_seconds",
        fallback=20.0,
    )

    user_agent = cfg.get(
        "xmplaylist",
        "user_agent",
        fallback="plex-playlist-importer/1.0",
    ).strip()

    client = xm_client or XMPlaylistClient(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )

    configured_state_path = Path(
        cfg.get(
            "xmplaylist",
            "state_database",
            fallback="cache/xmplaylist_history.db",
        )
    )

    if configured_state_path.is_absolute():
        state_path = configured_state_path
    else:
        state_path = (
            args.config.resolve().parent
            / configured_state_path
        )

    ingestion = ingest_station(
        client=client,
        station_number=args.xmstation,
        hours=history_hours,
        max_requests=max_requests,
        max_tracks=max_tracks,
        state_store=XMPlaylistStateStore(state_path),
    )

    playlist_name = args.playlist or ingestion.playlist_name

    logger.info(
        "XMPlaylist source resolved: channel %s - %s",
        ingestion.station.number,
        ingestion.station.name,
    )
    logger.info(
        "Target Plex playlist: %s",
        playlist_name,
    )

    if ingestion.partial:
        logger.warning(
            "XMPlaylist history is partial. Saved cursor will resume "
            "the backfill on the next run."
        )

    return list(ingestion.entries), playlist_name


def run_lidarr_diagnostics(
    *,
    cfg: configparser.ConfigParser,
    session: MatchingSession,
    output_path: Path,
    search_missing_albums: bool = False,
    client: LidarrClient | None = None,
    config_path: Path = Path("config.ini"),
    rejected_terms: tuple[str, ...] | list[str] | None = None,
) -> list[LidarrDiagnosticRow]:
    """
    Check Plex-unmatched entries against Lidarr and write a CSV report.

    When ``search_missing_albums`` is true, matching missing albums are
    queued for search. The command is intentionally not polled here:
    scheduled runs should finish promptly and re-evaluate Plex availability
    during the next synchronization.
    """

    if not cfg.has_section("lidarr"):
        raise RuntimeError(
            "Lidarr operations require a [lidarr] section in config.ini"
        )

    lidarr_enabled = cfg.getboolean(
        "lidarr",
        "enabled",
        fallback=False,
    )

    if not lidarr_enabled:
        raise RuntimeError(
            "Lidarr integration is disabled. "
            "Set [lidarr] enabled = true."
        )

    lidarr_url = cfg.get(
        "lidarr",
        "url",
        fallback="",
    ).strip()

    lidarr_api_key = cfg.get(
        "lidarr",
        "api_key",
        fallback="",
    ).strip()

    timeout_seconds = cfg.getfloat(
        "lidarr",
        "timeout_seconds",
        fallback=20.0,
    )

    if not lidarr_url:
        raise RuntimeError(
            "Lidarr URL is empty. Set [lidarr] url in config.ini."
        )

    if not lidarr_api_key:
        raise RuntimeError(
            "Lidarr API key is empty. Set [lidarr] api_key in config.ini."
        )

    if timeout_seconds <= 0:
        raise RuntimeError(
            "Lidarr timeout_seconds must be greater than zero."
        )

    client = client or LidarrClient(
        url=lidarr_url,
        api_key=lidarr_api_key,
        timeout_seconds=timeout_seconds,
    )

    health = client.is_available()
    if not health.available:
        raise RuntimeError(f"Lidarr unavailable: {health.detail}")
    logger.info("Connected to Lidarr: %s", health.detail)

    unmatched_count = sum(
        1 for result in session.results
        if result.matched is None
    )
    unique_artist_count = count_unique_unmatched_artists(
        session.results
    )
    logger.info("Lidarr diagnostics")
    logger.info("------------------")
    logger.info("Unmatched tracks : %d", unmatched_count)
    logger.info("Unique artists   : %d", unique_artist_count)
    logger.info(
        "Album searches  : %s",
        "enabled" if search_missing_albums else "disabled",
    )

    progress_step = max(1, unmatched_count // 10)

    def log_progress(
        completed: int,
        total: int,
        _entry: object,
    ) -> None:
        if (
            completed == 1
            or completed == total
            or completed % progress_step == 0
        ):
            logger.info(
                "Lidarr progress: %d/%d",
                completed,
                total,
            )

    remember_searches = cfg.getboolean(
        "lidarr",
        "remember_failed_searches",
        fallback=True,
    )
    retry_after_days = cfg.getfloat(
        "lidarr",
        "retry_search_after_days",
        fallback=7.0,
    )
    if retry_after_days < 0:
        raise RuntimeError(
            "Lidarr retry_search_after_days must be zero or greater."
        )

    history_path = resolve_config_path(
        config_path,
        cfg.get(
            "lidarr",
            "search_history_database",
            fallback="cache/lidarr_search_history.db",
        ),
    )
    history_store = (
        LidarrSearchHistoryStore(history_path)
        if remember_searches
        else None
    )

    rows = build_lidarr_diagnostics(
        results=session.results,
        client=client,
        search_missing_albums=search_missing_albums,
        history_store=history_store,
        remember_searches=remember_searches,
        retry_after_days=retry_after_days,
        progress_callback=log_progress,
        rejected_terms=rejected_terms,
    )

    write_lidarr_diagnostic_csv(
        rows,
        output_path,
    )

    logger.info(
        "Lidarr diagnostics complete: %d unmatched entries",
        len(rows),
    )

    logger.info(
        "Lidarr report written: %s",
        output_path,
    )

    log_lidarr_summary(rows)
    return rows


def log_lidarr_summary(
    rows: list[LidarrDiagnosticRow],
) -> None:
    """Log a compact, human-readable Lidarr result summary."""

    summary = summarize_lidarr_diagnostics(rows)
    for line in format_lidarr_summary(summary):
        logger.info(line)



def _analytics_match_counts(session: MatchingSession) -> tuple[int, int, int]:
    normal = fallback = alias = 0
    for result in session.results:
        if result.matched is None:
            continue
        reason = str(getattr(result, "reason", "") or "").casefold()
        if "fallback" in reason:
            fallback += 1
        else:
            normal += 1
        if "alias" in reason:
            alias += 1
    return normal, fallback, alias


def write_run_analytics(
    *,
    args,
    cfg,
    session,
    playlist_name,
    run_status,
    lidarr_rows,
    run_duration_seconds: float,
) -> None:
    if not cfg.getboolean("analytics", "enabled", fallback=True):
        return
    normal, fallback, alias = _analytics_match_counts(session)
    unmatched = sum(1 for result in session.results if result.matched is None)
    lidarr = count_lidarr_states(lidarr_rows)
    source = f"XMPlaylist Ch {args.xmstation}" if args.xmstation is not None else str(args.input_file)
    item = RunAnalytics.create(
        source=source,
        playlist=playlist_name,
        requested_tracks=len(session.results),
        normal_matches=normal,
        fallback_matches=fallback,
        alias_matches=alias,
        unmatched_tracks=unmatched,
        metadata_warnings=count_metadata_warnings(session, {}),
        lidarr_searches_queued=lidarr["queued"],
        lidarr_searches_suppressed=lidarr["suppressed"],
        lidarr_retries_queued=lidarr["retries"],
        lidarr_tracks_available=lidarr["available"],
        run_duration_seconds=round(run_duration_seconds, 3),
        cache_refresh_performed=run_status.cache_refreshed,
        stale_plex_matches=run_status.stale_plex_matches,
        playlist_skip_reason=run_status.playlist_skip_reason,
        plex_cache_age_hours=run_status.cache_age_hours,
        plex_cache_track_count=run_status.cache_track_count,
        plex_state=run_status.plex.state.value,
        xmplaylist_state=run_status.xmplaylist.state.value,
        lidarr_state=run_status.lidarr.state.value,
        tidal_state=run_status.tidal.state.value,
        playlist_state=run_status.playlist_state,
        run_result="COMPLETED WITH WARNINGS" if run_status.has_warnings else "SUCCESS",
    )
    history = Path(cfg.get("analytics", "history_csv", fallback="reports/match_analytics.csv"))
    latest = Path(cfg.get("analytics", "latest_json", fallback="reports/latest_run.json"))
    if not history.is_absolute():
        history = args.config.resolve().parent / history
    if not latest.is_absolute():
        latest = args.config.resolve().parent / latest
    append_match_analytics_csv(item, history)
    write_latest_run_json(item, latest)
    logger.info("Match analytics appended: %s", history)
    logger.info("Latest run status written: %s", latest)


def _health_text(health: ComponentHealth) -> str:
    checked = "" if health.checked else " (not checked)"
    detail = f" - {health.detail}" if health.detail else ""
    return f"{health.state.value}{checked}{detail}"


def log_run_summary(run_status: RunStatus) -> None:
    logger.info("Run summary:")
    age_text = (
        f", {run_status.cache_age_hours:.2f} hours old"
        if run_status.cache_age_hours is not None
        else ""
    )
    logger.info(
        "  Cache      : %s",
        _health_text(run_status.cache),
    )
    logger.info(
        "  Plex cache : %s (%d tracks%s)",
        run_status.cache_state,
        run_status.cache_track_count,
        age_text,
    )
    logger.info("  Plex       : %s", _health_text(run_status.plex))
    logger.info(
        "  XMPlaylist : %s",
        _health_text(run_status.xmplaylist),
    )
    logger.info("  Lidarr     : %s", _health_text(run_status.lidarr))
    logger.info("  TIDAL      : %s", _health_text(run_status.tidal))
    logger.info("  Playlist   : %s", run_status.playlist_state)
    if run_status.stale_plex_matches:
        logger.info(
            "  Stale cache: %d unresolved Plex match(es)",
            run_status.stale_plex_matches,
        )
    if run_status.playlist_skip_reason:
        logger.info(
            "  Skip reason: %s",
            run_status.playlist_skip_reason,
        )
    logger.info(
        "  Result     : %s",
        "COMPLETED WITH WARNINGS"
        if run_status.has_warnings
        else "SUCCESS",
    )



def resolve_alias_path(
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> Path:
    configured = Path(
        cfg.get(
            "artist_aliases",
            "file",
            fallback="resources/aliases.txt",
        )
    )
    if configured.is_absolute():
        return configured
    return config_path.resolve().parent / configured


def resolve_alias_usage_path(
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> Path:
    configured = Path(
        cfg.get(
            "alias_intelligence",
            "usage_database",
            fallback="cache/alias_usage.db",
        )
    )
    if configured.is_absolute():
        return configured
    return config_path.resolve().parent / configured


def record_alias_effectiveness(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
    session: MatchingSession,
    aliases: dict[str, str],
    source: str,
    playlist: str,
) -> None:
    if not cfg.getboolean(
        "alias_intelligence",
        "track_usage",
        fallback=True,
    ):
        return

    usage_counts = count_alias_usage(
        results=session.results,
        aliases=aliases,
    )
    store = AliasUsageStore(
        resolve_alias_usage_path(cfg, config_path)
    )
    store.initialize()
    store.record_run(
        usage_counts=usage_counts,
        aliases=aliases,
        source=source,
        playlist=playlist,
    )

    logger.info(
        "Alias effectiveness updated: %d aliases used, %d matches",
        len(usage_counts),
        sum(usage_counts.values()),
    )



def resolve_alias_suggestion_inputs(
    patterns: list[str] | None,
    *,
    default_path: Path,
) -> list[Path]:
    """Resolve explicit alias-input paths/globs or use the configured default."""

    if not patterns:
        candidates = [Path(default_path)]
    else:
        candidates: list[Path] = []
        for pattern in patterns:
            matches = [Path(value) for value in glob.glob(pattern)]
            if not matches:
                raise RuntimeError(
                    f"Alias suggestion input matched no files: {pattern}"
                )
            candidates.extend(matches)

    resolved: dict[str, Path] = {}
    for candidate in candidates:
        path = candidate.expanduser()
        if not path.exists():
            raise RuntimeError(
                f"Alias suggestion input file not found: {path}"
            )
        if not path.is_file():
            raise RuntimeError(
                f"Alias suggestion input is not a file: {path}"
            )
        if path.suffix.casefold() != ".csv":
            raise RuntimeError(
                f"Alias suggestion input must be a CSV file: {path}"
            )
        absolute = path.resolve()
        resolved[str(absolute).casefold()] = absolute

    return sorted(resolved.values(), key=lambda value: str(value).casefold())

def run_library_intelligence(
    *,
    args,
    cfg: configparser.ConfigParser,
    cache: LibraryCache,
) -> bool:
    requested = any([
        args.export_artists,
        args.suggest_aliases is not None,
        args.import_aliases is not None,
        args.audit_aliases,
    ])
    if not requested:
        return False

    tracks = cache.load_tracks()
    aliases_path = resolve_alias_path(cfg, args.config)

    if args.export_artists:
        rows = export_plex_artists_csv(
            tracks,
            args.artists_output,
        )
        logger.info(
            "Plex artist inventory written: %s (%d artists)",
            args.artists_output,
            len(rows),
        )

    if args.suggest_aliases is not None:
        input_paths = resolve_alias_suggestion_inputs(
            args.suggest_aliases,
            default_path=args.unmatched,
        )
        rows = suggest_aliases_csv(
            unmatched_csv=input_paths,
            tracks=tracks,
            aliases_path=aliases_path,
            output_path=args.alias_suggestions_output,
        )
        logger.info(
            "Alias suggestions written: %s (%d rows from %d input file(s))",
            args.alias_suggestions_output,
            len(rows),
            len(input_paths),
        )

    if args.import_aliases is not None:
        summary = import_approved_aliases(
            suggestions_csv=args.import_aliases,
            aliases_path=aliases_path,
        )
        logger.info(
            "Alias import complete: added=%d existing=%d "
            "ignored=%d invalid=%d total=%d",
            summary["added"],
            summary["skipped_existing"],
            summary["ignored"],
            summary["invalid"],
            summary["total"],
        )

    if args.audit_aliases:
        usage_store = AliasUsageStore(
            resolve_alias_usage_path(cfg, args.config)
        )
        rows = audit_aliases_csv(
            aliases_path=aliases_path,
            tracks=tracks,
            output_path=args.alias_audit_output,
            usage_store=usage_store,
            review_after_days=cfg.getfloat(
                "alias_intelligence",
                "review_after_days",
                fallback=90.0,
            ),
        )
        logger.info(
            "Alias audit written: %s (%d aliases)",
            args.alias_audit_output,
            len(rows),
        )

    return True


def run_tidal_search_diagnostic(
    *,
    args,
    cfg: configparser.ConfigParser,
    matching_config: MatchingConfig,
) -> None:
    """Run a read-only TIDAL search diagnostic and print sanitized results."""

    if not cfg.has_section("tidal"):
        raise RuntimeError("Missing [tidal] section in configuration.")

    tidal_cfg = cfg["tidal"]
    client_id = tidal_cfg.get("client_id", "").strip()
    client_secret = tidal_cfg.get("client_secret", "").strip()

    if not client_id or not client_secret:
        raise RuntimeError(
            "TIDAL client_id and client_secret are required for --tidal-search."
        )

    artist, title = args.tidal_search

    client = TidalClient(
        client_id=client_id,
        client_secret=client_secret,
        country_code=tidal_cfg.get("country_code", "US"),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
        hydration_delay_seconds=tidal_cfg.getfloat(
            "hydration_delay_seconds",
            fallback=0.25,
        ),
    )

    try:
        candidates = client.search_tracks(artist, title)
    except TidalError as exc:
        raise RuntimeError(str(exc)) from exc

    allow_explicit = tidal_cfg.getboolean(
        "allow_explicit",
        fallback=True,
    )

    accepted = qualifying_candidates(
        requested_artist=artist,
        requested_title=title,
        candidates=candidates,
        artist_aliases=matching_config.artist_aliases,
        allow_explicit=allow_explicit,
        rejected_terms=matching_config.rejected_terms,
    )

    print(
        format_tidal_search_results(
            requested_artist=artist,
            requested_title=title,
            candidates=candidates,
            accepted=accepted,
            artist_aliases=matching_config.artist_aliases,
            allow_explicit=allow_explicit,
            rejected_terms=matching_config.rejected_terms,
        )
    )


def run_tidal_unmatched_resolution(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
    session,
    matching_config: MatchingConfig,
    run_status: RunStatus,
    playlist_name: str,
    dry_run: bool,
) -> tuple[int, int, tuple | None]:
    """
    Resolve Plex-unmatched entries in TIDAL.

    In a real run, matched TIDAL tracks are additively synchronized to a
    same-named companion playlist. Dry runs never modify TIDAL state.
    """

    if not cfg.has_section("tidal"):
        run_status.tidal = ComponentHealth.not_configured(
            "missing [tidal] configuration"
        )
        return (0, 0, None)

    tidal_cfg = cfg["tidal"]
    if not tidal_cfg.getboolean("enabled", fallback=False):
        run_status.tidal = ComponentHealth.disabled("disabled in configuration")
        return (0, 0, None)

    client_id = tidal_cfg.get("client_id", "").strip()
    client_secret = tidal_cfg.get("client_secret", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(
            "TIDAL is enabled but client_id/client_secret are missing."
        )

    client = TidalClient(
        client_id=client_id,
        client_secret=client_secret,
        country_code=tidal_cfg.get("country_code", "US"),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
        hydration_delay_seconds=tidal_cfg.getfloat(
            "hydration_delay_seconds",
            fallback=0.25,
        ),
    )

    cache = None
    if tidal_cfg.getboolean("cache_enabled", fallback=True):
        cache_path = Path(
            tidal_cfg.get(
                "cache_database",
                "cache/tidal_search_cache.db",
            )
        )
        if not cache_path.is_absolute():
            cache_path = config_path.parent / cache_path

        cache = TidalSearchCache(
            cache_path,
            max_age_hours=tidal_cfg.getfloat(
                "cache_max_age_hours",
                fallback=24.0,
            ),
        )
        cache.initialize()

    quality_config = parse_quality_preference(
        tidal_cfg.get(
            "quality_preference",
            "DOLBY_ATMOS,HIRES_LOSSLESS,LOSSLESS",
        )
    )
    for warning in quality_config.warnings:
        logger.warning("TIDAL configuration: %s", warning)

    logger.info(
        "TIDAL quality preference: %s",
        " > ".join(quality_config.values),
    )

    allow_explicit = tidal_cfg.getboolean(
        "allow_explicit",
        fallback=True,
    )
    logger.info(
        "TIDAL explicit content: %s",
        "allowed" if allow_explicit else "rejected by configuration",
    )

    service = TidalSearchService(
        client=client,
        cache=cache,
        artist_aliases=matching_config.artist_aliases,
        quality_preference=quality_config.values,
        allow_explicit=allow_explicit,
        rejected_terms=matching_config.rejected_terms,
    )

    unmatched = [
        result.requested
        for result in session.results
        if result.matched is None
    ]

    matched_count = 0
    searched_count = 0
    matched_track_ids: list[str] = []
    matched_track_metadata: dict[str, tuple[str, str, str]] = {}
    matched_candidates = []
    unmatched_diagnostic_rows = []

    for entry in unmatched:
        resolution = service.resolve(entry.artist, entry.title)
        searched_count += 1

        if resolution.matched is None:
            if resolution.inconclusive:
                failed_ids = ",".join(
                    failure.track_id
                    for failure in resolution.hydration_failures
                )
                logger.warning(
                    "TIDAL resolution inconclusive: %s - %s; "
                    "candidate hydration failed for track(s) %s; "
                    "NO_MATCH was not cached",
                    entry.artist,
                    entry.title,
                    failed_ids or "<unknown>",
                )
            else:
                logger.info(
                    "TIDAL no match: %s - %s (%s)",
                    entry.artist,
                    entry.title,
                    resolution.source,
                )
            unmatched_diagnostic_rows.extend(
                build_tidal_unmatched_rows(
                    requested_artist=entry.artist,
                    requested_title=entry.title,
                    resolution=resolution,
                    artist_aliases=matching_config.artist_aliases,
                    allow_explicit=allow_explicit,
                    rejected_terms=matching_config.rejected_terms,
                )
            )
            continue

        matched_count += 1
        candidate = resolution.matched
        matched_candidates.append(candidate)
        matched_track_ids.append(candidate.track_id)
        matched_track_metadata[candidate.track_id] = (
            candidate.artist,
            candidate.title,
            candidate.album,
        )
        logger.info(
            "TIDAL match: %s - %s -> %s - %s "
            "[%s] quality=%s (%s)",
            entry.artist,
            entry.title,
            candidate.artist,
            candidate.title,
            candidate.track_id,
            candidate.quality or "unknown",
            resolution.source,
        )

    logger.info(
        "TIDAL catalog resolution complete: %d/%d unmatched track(s) found",
        matched_count,
        searched_count,
    )

    reports_directory = Path(
        cfg.get("reports", "directory", fallback="reports").strip()
        or "reports"
    )
    if not reports_directory.is_absolute():
        reports_directory = config_path.parent / reports_directory

    tidal_match_report = write_tidal_matched_report(
        candidates=matched_candidates,
        reports_directory=reports_directory,
    )
    if tidal_match_report is not None:
        logger.info("TIDAL matched-track report written: %s", tidal_match_report)

    tidal_unmatched_report = write_tidal_unmatched_report(
        rows=unmatched_diagnostic_rows,
        reports_directory=reports_directory,
    )
    if tidal_unmatched_report is not None:
        logger.info(
            "TIDAL unmatched-track report written: %s",
            tidal_unmatched_report,
        )

    companion_detail = "no companion update required"
    pending_reconciliation = None

    if matched_track_ids:
        if dry_run:
            unique_count = len(set(matched_track_ids))
            companion_detail = (
                f"dry-run; would sync {unique_count} TIDAL track(s) "
                f"to companion playlist {playlist_name!r}"
            )
            logger.info("TIDAL companion %s", companion_detail)
        else:
            tidal_cfg, token_file = _tidal_user_settings(
                cfg=cfg,
                config_path=config_path,
            )

            store = TidalTokenStore(token_file)
            tokens = store.load()
            granted = {scope for scope in tokens.scope.split() if scope}
            required = {
                "playlists.read",
                "playlists.write",
                "collection.read",
                "collection.write",
            }
            missing = sorted(required - granted)
            if missing:
                raise RuntimeError(
                    "Saved TIDAL user token lacks required playlist scope(s): "
                    + ", ".join(missing)
                    + ". Run --tidal-authorize-write first."
                )

            account_client = _build_tidal_account_client(
                tidal_cfg=tidal_cfg,
                token_file=token_file,
            )

            state_db = Path(
                tidal_cfg.get(
                    "state_database",
                    "cache/tidal_state.db",
                )
            )
            if not state_db.is_absolute():
                state_db = config_path.parent / state_db

            companion = TidalCompanionPlaylistService(
                account_client,
                state_store=TidalStateStore(state_db),
            )
            sync = companion.add_missing_tracks(
                playlist_name=playlist_name,
                track_ids=matched_track_ids,
                metadata_by_track_id=matched_track_metadata,
            )

            state = "created" if sync.playlist_created else "reused"
            companion_detail = (
                f"{state} companion {sync.playlist.name!r}; "
                f"playlist_added={len(sync.added_track_ids)}; "
                f"playlist_existing={len(sync.existing_track_ids)}; "
                f"favorites_added={len(sync.favorite_added_track_ids)}; "
                f"favorites_existing={len(sync.favorite_existing_track_ids)}"
            )
            logger.info(
                "TIDAL state recorded: %d track membership(s) -> %s",
                sync.requested_track_count,
                state_db,
            )
            logger.info(
                "TIDAL companion playlist: %s [%s]; "
                "playlist_added=%d; playlist_existing=%d; "
                "favorites_added=%d; favorites_existing=%d",
                sync.playlist.name,
                sync.playlist.playlist_id,
                len(sync.added_track_ids),
                len(sync.existing_track_ids),
                len(sync.favorite_added_track_ids),
                len(sync.favorite_existing_track_ids),
            )

            planner = TidalReconciliationPlanner(
                TidalStateStore(state_db)
            )
            decisions = planner.plan(
                playlist_name=playlist_name,
                desired_track_ids=matched_track_ids,
            )

            reconcile_counts: dict[str, int] = {}
            for decision in decisions:
                key = decision.action.value
                reconcile_counts[key] = reconcile_counts.get(key, 0) + 1

                if decision.action != TidalReconcileAction.KEEP:
                    logger.info(
                        "TIDAL reconcile plan: %s track=%s playlist=%s; %s",
                        decision.action.value,
                        decision.track_id,
                        decision.playlist_name,
                        decision.reason,
                    )

            if decisions:
                summary = ", ".join(
                    f"{key}={value}"
                    for key, value in sorted(reconcile_counts.items())
                )
                logger.info(
                    "TIDAL reconciliation plan: %s",
                    summary,
                )

                pending_reconciliation = (
                    account_client,
                    state_db,
                    decisions,
                )
                logger.info(
                    "TIDAL reconciliation deferred until Plex playlist "
                    "update succeeds"
                )

    run_status.tidal = ComponentHealth.available_health(
        f"catalog resolution {matched_count}/{searched_count}; "
        f"{companion_detail}"
    )

    return matched_count, searched_count, pending_reconciliation


def _tidal_user_settings(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> tuple[configparser.SectionProxy, Path]:
    if not cfg.has_section("tidal"):
        raise RuntimeError("Missing [tidal] section in configuration.")

    tidal_cfg = cfg["tidal"]
    token_file = Path(
        tidal_cfg.get(
            "user_token_file",
            "cache/tidal_user_tokens.json",
        )
    )
    if not token_file.is_absolute():
        token_file = config_path.parent / token_file

    return tidal_cfg, token_file


def run_tidal_authorize(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )

    client_id = tidal_cfg.get("client_id", "").strip()
    if not client_id:
        raise RuntimeError("TIDAL client_id is required.")

    redirect_uri = tidal_cfg.get(
        "redirect_uri",
        "http://127.0.0.1:8765/callback",
    ).strip()

    tokens = authorize_interactively(
        client_id=client_id,
        redirect_uri=redirect_uri,
        token_store=TidalTokenStore(token_file),
        timeout_seconds=tidal_cfg.getint(
            "authorization_timeout_seconds",
            fallback=180,
        ),
        request_timeout=tidal_cfg.getfloat(
            "timeout",
            fallback=20.0,
        ),
    )

    print("")
    print("TIDAL user authorization completed.")
    print(f"Token store: {token_file}")
    print(f"Granted scope: {tokens.scope or '<server did not echo scope>'}")


def run_tidal_authorize_write(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )

    client_id = tidal_cfg.get("client_id", "").strip()
    if not client_id:
        raise RuntimeError("TIDAL client_id is required.")

    redirect_uri = tidal_cfg.get(
        "redirect_uri",
        "http://127.0.0.1:8765/callback",
    ).strip()

    tokens = authorize_interactively(
        client_id=client_id,
        redirect_uri=redirect_uri,
        token_store=TidalTokenStore(token_file),
        timeout_seconds=tidal_cfg.getint(
            "authorization_timeout_seconds",
            fallback=180,
        ),
        request_timeout=tidal_cfg.getfloat(
            "timeout",
            fallback=20.0,
        ),
        scopes=WRITE_SCOPES,
    )

    print("")
    print("TIDAL user write authorization completed.")
    print(f"Token store: {token_file}")
    print(f"Granted scope: {tokens.scope or '<server did not echo scope>'}")


def run_tidal_write_test(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )

    store = TidalTokenStore(token_file)
    tokens = store.load()
    granted = {scope for scope in tokens.scope.split() if scope}
    required = {"playlists.write"}
    missing = sorted(required - granted)
    if missing:
        raise RuntimeError(
            "Saved TIDAL user token lacks required write scope(s): "
            + ", ".join(missing)
            + ". Run --tidal-authorize-write first."
        )

    provider = TidalUserTokenProvider(
        client_id=tidal_cfg.get("client_id", "").strip(),
        store=store,
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
    )
    client = TidalAccountClient(
        token_provider=provider,
        country_code=tidal_cfg.get("country_code", "US"),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
    )

    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"PPI WRITE TEST {stamp}"
    created = None

    print("")
    print("TIDAL WRITE TEST — REVERSIBLE TEMPORARY PLAYLIST")
    print(f"Creating: {name}")
    try:
        created = client.create_playlist(
            name,
            description=(
                "Temporary playlist created by Plex Playlist Importer "
                "write diagnostics; safe to delete."
            ),
            access_type="UNLISTED",
        )
        print(f"Created: {created.name} [{created.playlist_id}]")

        verified = client.get_playlist(created.playlist_id)
        if verified.playlist_id != created.playlist_id:
            raise RuntimeError("TIDAL write test verification ID mismatch.")
        if verified.name != name:
            raise RuntimeError(
                "TIDAL write test verification name mismatch: "
                f"expected {name!r}, got {verified.name!r}"
            )
        print("Verified: temporary playlist is readable through the API")
    finally:
        if created is not None:
            client.delete_playlist(created.playlist_id)
            print(f"Deleted: {created.name} [{created.playlist_id}]")

    print("TIDAL write test completed successfully.")


def _tidal_favorite_test_marker_path(
    *,
    config_path: Path,
) -> Path:
    return config_path.parent / "cache" / "tidal_favorite_test_state.json"


def _write_tidal_favorite_test_marker(
    path: Path,
    *,
    track_id: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "track_id": track_id,
                "original_state": "not_favorite",
                "purpose": "reversible_tidal_favorite_test",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _clear_tidal_favorite_test_marker(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _build_tidal_account_client(
    *,
    tidal_cfg: configparser.SectionProxy,
    token_file: Path,
) -> TidalAccountClient:
    provider = TidalUserTokenProvider(
        client_id=tidal_cfg.get("client_id", "").strip(),
        store=TidalTokenStore(token_file),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
    )
    return TidalAccountClient(
        token_provider=provider,
        country_code=tidal_cfg.get("country_code", "US"),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
        rate_limit_retries=tidal_cfg.getint(
            "account_rate_limit_retries",
            fallback=3,
        ),
        rate_limit_fallback_seconds=tidal_cfg.getfloat(
            "account_rate_limit_fallback_seconds",
            fallback=5.0,
        ),
    )


def run_tidal_favorite_test(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )

    store = TidalTokenStore(token_file)
    tokens = store.load()
    granted = {scope for scope in tokens.scope.split() if scope}
    missing = sorted({"collection.read", "collection.write"} - granted)
    if missing:
        raise RuntimeError(
            "Saved TIDAL user token lacks required collection scope(s): "
            + ", ".join(missing)
            + ". Run --tidal-authorize-write first."
        )

    client = _build_tidal_account_client(
        tidal_cfg=tidal_cfg,
        token_file=token_file,
    )

    track_id = "317688870"
    marker = _tidal_favorite_test_marker_path(config_path=config_path)

    print("")
    print("TIDAL FAVORITE TEST — REVERSIBLE")
    print("Track: Steely Dan - Peg [317688870]")

    if marker.exists():
        print("Recovery marker found from an interrupted prior test.")
        if client.is_favorite_track(track_id):
            client.remove_favorite_track(track_id)
            print("Recovery: removed prior temporary Peg favorite")
        _clear_tidal_favorite_test_marker(marker)

    if client.is_favorite_track(track_id):
        raise RuntimeError(
            "Safety stop: Peg is already a TIDAL favorite and no PPI recovery "
            "marker claims ownership. No account changes were made."
        )

    print("Pre-check: Peg is not currently favorited")
    added = False
    _write_tidal_favorite_test_marker(marker, track_id=track_id)

    try:
        client.add_favorite_track(track_id)
        added = True
        print("Added: Peg to TIDAL favorites")

        if not client.is_favorite_track(track_id):
            raise RuntimeError(
                "TIDAL favorite test failed: Peg was not visible after add."
            )
        print("Verified: Peg is present in TIDAL favorites")
    finally:
        if added:
            client.remove_favorite_track(track_id)
            print("Removed: Peg from TIDAL favorites")

    if client.is_favorite_track(track_id):
        raise RuntimeError(
            "TIDAL favorite test cleanup failed: Peg remains favorited."
        )

    _clear_tidal_favorite_test_marker(marker)
    print("Verified: original non-favorite state restored")
    print("TIDAL favorite test completed successfully.")


def run_tidal_favorite_cleanup(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )
    client = _build_tidal_account_client(
        tidal_cfg=tidal_cfg,
        token_file=token_file,
    )

    track_id = "317688870"
    print("")
    print("TIDAL FAVORITE CLEANUP")
    print("Target only: Steely Dan - Peg [317688870]")

    if client.is_favorite_track(track_id):
        client.remove_favorite_track(track_id)
        print("Removed: Peg from TIDAL favorites")
    else:
        print("Peg is already absent; nothing to remove")

    if client.is_favorite_track(track_id):
        raise RuntimeError("Cleanup failed: Peg remains favorited.")

    _clear_tidal_favorite_test_marker(
        _tidal_favorite_test_marker_path(config_path=config_path)
    )
    print("Verified: Peg is not a TIDAL favorite.")
    print("Other favorite tracks were not modified.")



def run_tidal_account_test(
    *,
    cfg: configparser.ConfigParser,
    config_path: Path,
) -> None:
    tidal_cfg, token_file = _tidal_user_settings(
        cfg=cfg,
        config_path=config_path,
    )

    provider = TidalUserTokenProvider(
        client_id=tidal_cfg.get("client_id", "").strip(),
        store=TidalTokenStore(token_file),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
    )

    client = TidalAccountClient(
        token_provider=provider,
        country_code=tidal_cfg.get("country_code", "US"),
        timeout=tidal_cfg.getfloat("timeout", fallback=20.0),
    )

    summary = client.summary()

    print("")
    print("TIDAL USER ACCOUNT — READ ONLY")
    print(f"Owned playlists: {len(summary.playlists)}")
    for playlist in summary.playlists:
        print(f"  - {playlist.name or '<unnamed>'} [{playlist.playlist_id}]")
    print(f"Favorite tracks: {summary.favorite_track_count}")


# ============================================================
# Main
# ============================================================


def main() -> None:
    run_started = perf_counter()
    parser = build_parser()
    args = parser.parse_args()

    profile_actions = sum(bool(value) for value in (
        args.xmprofile,
        args.all_xmprofiles,
        args.list_xmprofiles,
    ))
    if profile_actions > 1:
        parser.error(
            "Use only one of --xmprofile, --all-xmprofiles, "
            "or --list-xmprofiles."
        )

    profiles_path = args.xmstations_file
    if not profiles_path.is_absolute():
        profiles_path = args.config.resolve().parent / profiles_path

    if profile_actions:
        try:
            profiles = load_xmstation_profiles(profiles_path)
        except XMStationProfileError as exc:
            parser.error(str(exc))

        if args.list_xmprofiles:
            print(format_profile_listing(profiles.values()))
            return

        if args.all_xmprofiles:
            if args.input_file is not None or args.xmstation is not None:
                parser.error(
                    "--all-xmprofiles cannot be combined with an input "
                    "file or --xmstation."
                )
            results = run_all_profiles(
                profiles=list(profiles.values()),
                script_path=Path(__file__).resolve(),
                config_path=args.config.resolve(),
                profiles_path=profiles_path.resolve(),
                args=args,
            )
            sys.exit(aggregate_profile_exit_code(results))

        try:
            profile = get_xmstation_profile(profiles, args.xmprofile)
            if not profile.enabled:
                parser.error(
                    f"XMPlaylist profile '{profile.name}' is disabled"
                )
            apply_profile_to_args(args, profile)
        except XMStationProfileError as exc:
            parser.error(str(exc))

    cfg = load_config(args.config)

    trim_limit = (
        args.trim
        if args.trim is not None
        else cfg.getint("playlist", "trim", fallback=0)
    )
    if trim_limit < 0:
        parser.error("--trim must be 0 or greater")
    if trim_limit > 0 and (args.replace or args.sync):
        parser.error(
            "--trim cannot currently be used with --replace or --sync"
        )

    #
    # setup logging from config
    #
    logger = configure_logging(cfg, args.config)

    # Apply persistent report defaults unless the CLI explicitly overrides them.
    if args.unmatched is None:
        args.unmatched = resolve_report_path(
            cfg, args.config, key="unmatched", fallback_filename="unmatched.csv"
        )
    if args.report is None:
        args.report = resolve_report_path(
            cfg, args.config, key="match", fallback_filename="playlist_report.csv"
        )
    if args.lidarr_report is None:
        args.lidarr_report = resolve_report_path(
            cfg, args.config, key="lidarr", fallback_filename="lidarr_unmatched_report.csv"
        )

    run_status = RunStatus()
    include_file_paths = cfg.getboolean(
        "reports",
        "include_file_paths",
        fallback=False,
    )

    plex_cfg = cfg["plex"]

    url = plex_cfg.get("url")
    token = plex_cfg.get("token")
    library_name = plex_cfg.get("library", "Music")


    config = build_matching_config(
        cfg,
        args.config,
    )

    if args.tidal_search is not None:
        run_tidal_search_diagnostic(
            args=args,
            cfg=cfg,
            matching_config=config,
        )
        return

    if args.tidal_authorize:
        run_tidal_authorize(
            cfg=cfg,
            config_path=args.config,
        )
        return

    if args.tidal_authorize_write:
        run_tidal_authorize_write(
            cfg=cfg,
            config_path=args.config,
        )
        return

    if args.tidal_write_test:
        run_tidal_write_test(
            cfg=cfg,
            config_path=args.config,
        )
        return

    if args.tidal_favorite_cleanup:
        run_tidal_favorite_cleanup(
            cfg=cfg,
            config_path=args.config,
        )
        return

    if args.tidal_favorite_test:
        run_tidal_favorite_test(
            cfg=cfg,
            config_path=args.config,
        )
        return

    if args.tidal_account_test:
        run_tidal_account_test(
            cfg=cfg,
            config_path=args.config,
        )
        return

    
    # --------------------------------------------------------
    # Load library (cache or Plex)
    # --------------------------------------------------------


    cache_cfg = cfg["cache"]

    configured_cache_path = Path(
        cache_cfg.get(
            "database",
            "cache/plex_library.db",
        )
    )

    if configured_cache_path.is_absolute():
        cache_path = configured_cache_path
    else:
        cache_path = (
            args.config.resolve().parent
            / configured_cache_path
        )

    cache = LibraryCache(cache_path)
    cache.initialize()

    if run_library_intelligence(
        args=args,
        cfg=cfg,
        cache=cache,
    ):
        return

    plex = PlexClient(url, token, library_name)

    xm_client, lidarr_client = run_startup_health_checks(
        args=args,
        cfg=cfg,
        cache=cache,
        plex=plex,
        run_status=run_status,
    )

      # --------------------------------------------------------
    # Dedupe report
    # --------------------------------------------------------
    if args.dedupe:
        run_dedupe_report(
            cache=cache,
            output_path=args.output,
        )
        return

    max_age_hours = cache_cfg.getfloat("max_age_hours", fallback=24.0)

    index = load_search_index(
        cache=cache,
        plex=plex,
        use_cache=not args.no_cache,
        refresh_cache=args.refresh_cache,
        max_age_hours=max_age_hours,
        run_status=run_status,
    )

  
    # --------------------------------------------------------
    # Resolve input source and run matcher
    # --------------------------------------------------------

    entries, playlist_name = load_input_source(
        args=args,
        cfg=cfg,
        xm_client=xm_client,
    )

    session = run_matcher_entries(
        entries=entries,
        index=index,
        config=config,
    )

    
    # --------------------------------------------------------
    # Reports
    # --------------------------------------------------------

    generate_reports(
        session=session,
        unmatched_path=args.unmatched,
        report_path=args.report,
        artist_aliases=config.artist_aliases,
        include_file_paths=include_file_paths,
    )

    record_alias_effectiveness(
        cfg=cfg,
        config_path=args.config,
        session=session,
        aliases=config.artist_aliases,
        source=(
            f"XMPlaylist Ch {args.xmstation}"
            if args.xmstation is not None
            else str(args.input_file)
        ),
        playlist=playlist_name,
    )

    lidarr_rows: list[LidarrDiagnosticRow] = []

    external_unmatched_count = sum(
        1 for result in session.results if result.matched is None
    )
    tidal_dispatch_enabled = (
        cfg.has_section("tidal")
        and cfg.getboolean("tidal", "enabled", fallback=False)
    )
    logger.info(
        "External unmatched dispatch pool: %d track(s); Lidarr=%s; TIDAL=%s",
        external_unmatched_count,
        "enabled" if (args.lidarr_check or args.lidarr_search) else "not requested",
        "enabled" if tidal_dispatch_enabled else "disabled",
    )

    # --------------------------------------------------------
    # check lidarr
    # --------------------------------------------------------

    if args.lidarr_check or args.lidarr_search:
        try:
            if not run_status.lidarr.available:
                raise RuntimeError(
                    f"Lidarr unavailable: {run_status.lidarr.detail}"
                )

            lidarr_rows = run_lidarr_diagnostics(
                cfg=cfg,
                session=session,
                output_path=args.lidarr_report,
                search_missing_albums=args.lidarr_search,
                client=lidarr_client,
                config_path=args.config,
                rejected_terms=config.rejected_terms,
            )
            run_status.lidarr = ComponentHealth.available_health(
                "completed"
            )
        except Exception as exc:
            warning = f"Lidarr processing skipped: {exc}"
            logger.warning(warning)
            run_status.lidarr = ComponentHealth.unavailable(str(exc))
            run_status.warnings.append(warning)

    # --------------------------------------------------------
    # TIDAL unmatched resolution + additive companion playlist
    # --------------------------------------------------------

    pending_tidal_reconciliation = None

    try:
        (
            _tidal_matched_count,
            _tidal_searched_count,
            pending_tidal_reconciliation,
        ) = run_tidal_unmatched_resolution(
            cfg=cfg,
            config_path=args.config,
            session=session,
            matching_config=config,
            run_status=run_status,
            playlist_name=playlist_name,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        warning = f"TIDAL processing skipped: {exc}"
        logger.warning(warning)
        run_status.tidal = ComponentHealth.unavailable(str(exc))
        run_status.warnings.append(warning)

    # --------------------------------------------------------
    # Dry run
    # --------------------------------------------------------

    if args.dry_run:

        if trim_limit > 0:
            existing_playlist = plex.get_playlist(playlist_name)
            current_rating_keys = (
                [int(item.ratingKey) for item in existing_playlist.items()]
                if existing_playlist is not None
                else []
            )
            requested_rating_keys = [
                int(result.matched.rating_key)
                for result in session.results
                if result.matched is not None
            ]
            trim_preview = playlist_trim_preview(
                current_rating_keys=current_rating_keys,
                requested_rating_keys=requested_rating_keys,
                trim_limit=trim_limit,
            )
            logger.info(
                "Playlist trim preview: current=%d; new_unique=%d; "
                "after_update=%d; would_remove=%d; final=%d; limit=%d",
                trim_preview["current"],
                trim_preview["new_unique"],
                trim_preview["after_update"],
                trim_preview["remove"],
                trim_preview["final"],
                trim_limit,
            )

        run_status.playlist_state = "DRY RUN"
        if pending_tidal_reconciliation is not None:
            logger.info(
                "TIDAL destructive reconciliation skipped: dry-run; "
                "Plex playlist update not performed"
            )
        logger.info("Dry run complete (no playlist changes)")
        write_run_analytics(
            args=args,
            cfg=cfg,
            session=session,
            playlist_name=playlist_name,
            run_status=run_status,
            lidarr_rows=lidarr_rows,
            run_duration_seconds=perf_counter() - run_started,
        )
        log_run_summary(run_status)
        if run_status.has_warnings:
            sys.exit(2)
        return

    # --------------------------------------------------------
    # Playlist mode
    # --------------------------------------------------------

    mode = get_playlist_mode(args)

    # --------------------------------------------------------
    # Resolve + update playlist
    # --------------------------------------------------------

      
    expected_matches = sum(
        1
        for result in session.results
        if result.matched is not None
    )

    health = run_status.plex
    if not health.available:
        health = plex.is_available()
        run_status.plex = health

    if not health.available:
        warning = f"Plex playlist operation skipped because Plex is unavailable: {health.detail}"
        logger.warning(warning)
        run_status.playlist_state = "SKIPPED"
        run_status.warnings.append(warning)
        write_run_analytics(
            args=args,
            cfg=cfg,
            session=session,
            playlist_name=playlist_name,
            run_status=run_status,
            lidarr_rows=lidarr_rows,
            run_duration_seconds=perf_counter() - run_started,
        )
        log_run_summary(run_status)
        sys.exit(4)

    resolution = plex.resolve_matches(
        session.results
    )
    matched_tracks = resolution.tracks
    run_status.stale_plex_matches = len(
        resolution.stale_matches
    )

    if run_status.stale_plex_matches:
        warning = (
            f"{run_status.stale_plex_matches} cached Plex "
            "match(es) no longer exist. Run a Plex library scan, "
            "then rerun with --refresh-cache."
        )
        run_status.warnings.append(warning)

        if mode in {
            PlaylistMode.REPLACE,
            PlaylistMode.SYNC,
        }:
            run_status.playlist_state = "SKIPPED"
            run_status.playlist_skip_reason = "STALE_PLEX_CACHE"
            logger.warning(
                "Playlist %s skipped to prevent an incomplete "
                "or destructive update.",
                mode.name.lower(),
            )
            write_run_analytics(
                args=args,
                cfg=cfg,
                session=session,
                playlist_name=playlist_name,
                run_status=run_status,
                lidarr_rows=lidarr_rows,
                run_duration_seconds=perf_counter() - run_started,
            )
            log_run_summary(run_status)
            sys.exit(5)

        logger.warning(
            "Continuing playlist %s with %d valid resolved "
            "track(s); %d stale match(es) omitted.",
            mode.name.lower(),
            len(matched_tracks),
            run_status.stale_plex_matches,
        )

    if len(matched_tracks) + run_status.stale_plex_matches != expected_matches:
        warning = (
            "Plex resolution count was inconsistent: expected "
            f"{expected_matches}, resolved {len(matched_tracks)}, "
            f"stale {run_status.stale_plex_matches}."
        )
        logger.error(warning)
        run_status.playlist_state = "SKIPPED"
        run_status.playlist_skip_reason = "PLEX_RESOLUTION_MISMATCH"
        run_status.warnings.append(warning)
        write_run_analytics(
            args=args,
            cfg=cfg,
            session=session,
            playlist_name=playlist_name,
            run_status=run_status,
            lidarr_rows=lidarr_rows,
            run_duration_seconds=perf_counter() - run_started,
        )
        log_run_summary(run_status)
        sys.exit(5)

    plex.update_playlist(
        name=playlist_name,
        tracks=matched_tracks,
        mode=mode,
    )

    if trim_limit > 0:
        try:
            trim_result = plex.trim_playlist_fifo(
                name=playlist_name,
                max_tracks=trim_limit,
            )
            logger.info(
                "Playlist trim summary: limit=%d; removed=%d; final=%d",
                trim_limit,
                trim_result["removed"],
                trim_result["final"],
            )
        except Exception as exc:
            warning = (
                "Playlist update succeeded but FIFO trim failed: "
                f"limit={trim_limit}; {exc}"
            )
            logger.warning(warning)
            run_status.warnings.append(warning)


    run_status.playlist_state = (
        "UPDATED WITH WARNINGS"
        if run_status.stale_plex_matches
        else "UPDATED"
    )

    if pending_tidal_reconciliation is not None:
        (
            pending_account_client,
            pending_state_db,
            pending_decisions,
        ) = pending_tidal_reconciliation
        pending_state_store = TidalStateStore(pending_state_db)
        final_playlist = plex.get_playlist(playlist_name)
        final_playlist_items = (
            list(final_playlist.items())
            if final_playlist is not None
            else []
        )
        safe_pending_decisions = (
            filter_tidal_reconciliation_for_final_plex_membership(
                decisions=pending_decisions,
                state_store=pending_state_store,
                playlist_items=final_playlist_items,
                artist_aliases=config.artist_aliases,
            )
        )
        executor = TidalReconciliationExecutor(
            client=pending_account_client,
            state_store=pending_state_store,
        )
        execution = executor.execute(safe_pending_decisions)
        logger.info(
            "TIDAL reconciliation applied after confirmed Plex update: "
            "playlist_removed=%d; favorites_removed=%d; "
            "favorites_preserved=%d",
            len(execution.playlist_tracks_removed),
            len(execution.favorites_removed),
            len(execution.favorites_preserved),
        )

    logger.info("Done.")
    write_run_analytics(
        args=args,
        cfg=cfg,
        session=session,
        playlist_name=playlist_name,
        run_status=run_status,
        lidarr_rows=lidarr_rows,
        run_duration_seconds=perf_counter() - run_started,
    )
    log_run_summary(run_status)


# ============================================================
# Entry
# ============================================================

def cli() -> None:
    """Run the CLI and normalize Ctrl-C to process exit code 1."""
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)


if __name__ == "__main__":
    cli()
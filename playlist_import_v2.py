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

def load_config(path: Path) -> configparser.ConfigParser:

    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg


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

    return MatchingConfig(
        threshold=match_cfg.getfloat("threshold", 85),
        workers=match_cfg.getint("threads", 8),
        artist_weight=match_cfg.getfloat("artist_weight", 0.25),
        album_artist_weight=match_cfg.getfloat("album_artist_weight", 0.15),
        title_weight=match_cfg.getfloat("title_weight", 0.45),
        combined_weight=match_cfg.getfloat("combined_weight", 0.15),
        preferred_versions=preferred_versions,
        min_title_score=match_cfg.getfloat("min_title_score", 80),
        fallback_title_score=match_cfg.getfloat("fallback_title_score", 95),
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
        default=Path("unmatched.csv"),
        help="Unmatched-track CSV output path",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("playlist_report.csv"),
        help="Full match-report CSV output path",
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
        default=Path("lidarr_unmatched_report.csv"),
        help="Lidarr diagnostic CSV output path",
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
        action="store_true",
        help="Generate alias suggestions from the unmatched CSV",
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

    rows = build_lidarr_diagnostics(
        results=session.results,
        client=client,
        search_missing_albums=search_missing_albums,
        progress_callback=log_progress,
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


def run_library_intelligence(
    *,
    args,
    cfg: configparser.ConfigParser,
    cache: LibraryCache,
) -> bool:
    requested = any([
        args.export_artists,
        args.suggest_aliases,
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

    if args.suggest_aliases:
        rows = suggest_aliases_csv(
            unmatched_csv=args.unmatched,
            tracks=tracks,
            aliases_path=aliases_path,
            output_path=args.alias_suggestions_output,
        )
        logger.info(
            "Alias suggestions written: %s (%d rows)",
            args.alias_suggestions_output,
            len(rows),
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

    #
    # setup logging
    #
    logger = setup_logging()


    cfg = load_config(args.config)
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
    # Dry run
    # --------------------------------------------------------

    if args.dry_run:

        run_status.playlist_state = "DRY RUN"
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

    run_status.playlist_state = (
        "UPDATED WITH WARNINGS"
        if run_status.stale_plex_matches
        else "UPDATED"
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

if __name__ == "__main__":

    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
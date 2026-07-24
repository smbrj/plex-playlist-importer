from pathlib import Path


SOURCE = Path("playlist_import_v2.py").read_text(encoding="utf-8")


def _main_source() -> str:
    return SOURCE[SOURCE.index("def main("):]


def test_tidal_runtime_is_isolated_from_main_import_pipeline():
    main = _main_source()
    call = main.index("run_tidal_unmatched_resolution(")
    handler = main.index('warning = f"TIDAL processing skipped: {exc}"', call)

    assert "try:" in main[max(0, call - 200):call]
    assert handler > call
    assert "run_status.tidal = ComponentHealth.unavailable(str(exc))" in main[handler:handler + 500]
    assert "run_status.warnings.append(warning)" in main[handler:handler + 500]


def test_dry_run_with_external_warning_exits_two():
    main = _main_source()
    dry = main.index("if args.dry_run:")
    exit_two = main.index("sys.exit(2)", dry)

    assert "if run_status.has_warnings:" in main[dry:exit_two]


def test_post_plex_session_is_shared_with_lidarr_and_tidal():
    main = _main_source()
    matcher = main.index("session = run_matcher_entries(")
    dispatch = main.index("External unmatched dispatch pool:", matcher)
    lidarr = main.index("run_lidarr_diagnostics(", dispatch)
    tidal = main.index("run_tidal_unmatched_resolution(", dispatch)

    assert matcher < dispatch < lidarr < tidal
    assert "session=session" in main[lidarr:lidarr + 700]
    assert "session=session" in main[tidal:tidal + 700]


def test_xmplaylist_source_flows_into_same_matching_session():
    main = _main_source()
    source = main.index("entries, playlist_name = load_input_source(")
    matcher = main.index("session = run_matcher_entries(", source)
    dispatch = main.index("External unmatched dispatch pool:", matcher)

    assert source < matcher < dispatch
    assert "entries=entries" in main[matcher:matcher + 300]


def test_phase2_production_hooks_are_present():
    main = _main_source()

    assert "allow_explicit" in SOURCE
    assert "quality_preference" in SOURCE
    assert "write_tidal_matched_report(" in SOURCE
    assert "TidalCompanionPlaylistService(" in SOURCE
    assert "TidalReconciliationPlanner(" in SOURCE
    assert "TidalReconciliationExecutor(" in SOURCE
    assert "TidalStateStore(" in SOURCE


def test_temporary_cp016_ownership_cli_is_not_present():
    assert "--tidal-mark-test-owned" not in SOURCE

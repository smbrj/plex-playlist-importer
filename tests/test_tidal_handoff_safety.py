from pathlib import Path

SOURCE = Path("playlist_import_v2.py").read_text(encoding="utf-8")
MAIN = SOURCE[SOURCE.index("def main("):]
TIDAL_FN = SOURCE[
    SOURCE.index("def run_tidal_unmatched_resolution("):
    SOURCE.index("\ndef _tidal_user_settings(")
]


def test_tidal_helper_returns_pending_plan_without_destructive_execute():
    assert "pending_reconciliation = (" in TIDAL_FN
    assert "executor.execute(" not in TIDAL_FN
    assert (
        "return matched_count, searched_count, pending_reconciliation"
        in TIDAL_FN
    )


def test_tidal_helper_explicitly_logs_deferred_reconciliation():
    assert (
        "TIDAL reconciliation deferred until Plex playlist "
        in TIDAL_FN
    )
    assert "update succeeds" in TIDAL_FN


def test_destructive_tidal_execution_occurs_after_plex_update():
    update = MAIN.index("plex.update_playlist(")
    execute = MAIN.index("executor.execute(safe_pending_decisions)")
    assert update < execute


def test_destructive_execute_is_guarded_by_pending_plan():
    execute = MAIN.index("executor.execute(safe_pending_decisions)")
    guard = MAIN.rfind(
        "if pending_tidal_reconciliation is not None:", 0, execute
    )
    update = MAIN.index("plex.update_playlist(")
    assert update < guard < execute


def test_dry_run_exits_before_plex_update_and_destructive_execute():
    dry = MAIN.index("if args.dry_run:")
    update = MAIN.index("plex.update_playlist(")
    execute = MAIN.index("executor.execute(safe_pending_decisions)")
    dry_block = MAIN[dry:update]

    assert dry < update < execute
    assert "sys.exit(" in dry_block
    assert "TIDAL destructive reconciliation skipped" in dry_block


def test_success_log_names_confirmed_plex_update():
    assert (
        "TIDAL reconciliation applied after confirmed Plex update"
        in MAIN
    )

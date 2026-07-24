# TIDAL Phase 2 — Checkpoint-020

**Date:** 2026-07-23  
**Scope:** Phase 2 stabilization, closure validation, and production baseline

## Design decision

CP020 makes no production-code behavior changes.

The CP019 runtime is frozen while CP020 adds closure tests that verify:

- TIDAL failures are isolated from the main import pipeline;
- TIDAL failures update component health and warning state;
- warning-bearing dry runs exit with code 2;
- file and XMPlaylist sources flow through the same matcher;
- the resulting post-Plex MatchingSession is shared independently with Lidarr
  and TIDAL;
- explicit filtering, reporting, companion sync, state tracking, and
  reconciliation hooks remain present;
- the temporary CP016 ownership-forcing CLI remains removed.

A separate `TIDAL_PHASE2_BASELINE.md` records the final production policy and
the final representative XMPlaylist dry-run procedure.

## Validation

```powershell
python -m pytest tests/test_tidal_phase2_closure.py -v
python -m pytest -v
```

Then execute one representative XMPlaylist dry run:

```powershell
python playlist_import_v2.py --xmstation 14 --dry-run --lidarr-search --lidarr-report reports\lidarr_unmatched_report.csv
```

A configured `--xmprofile` may be used instead.

## Completion criterion

If the closure tests, full suite, and representative XMPlaylist dry run pass,
CP020 becomes the final TIDAL Phase 2 baseline.

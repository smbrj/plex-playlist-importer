# Checkpoint-021 — Plex-confirmed TIDAL handoff

## Purpose

Close the remaining TIDAL safety gap:

> A TIDAL fallback must not be destructively removed until the Plex playlist
> update for the current run has succeeded.

## New execution order

```text
Plex matching
  -> Lidarr / TIDAL additive processing
  -> TIDAL reconciliation planning only
  -> Plex playlist update
  -> destructive TIDAL reconciliation
```

`run_tidal_unmatched_resolution()` now returns a pending reconciliation plan.
It no longer executes DELETE/unfavorite actions itself.

If the run exits, skips, or raises before `plex.update_playlist(...)` completes,
the pending destructive plan is never executed.

Dry-run exits before Plex playlist mutation and therefore before destructive
TIDAL reconciliation.

A successful real handoff logs:

```text
TIDAL reconciliation deferred until Plex playlist update succeeds
...
TIDAL reconciliation applied after confirmed Plex update: ...
```

Existing exit-code semantics are unchanged.

## Validation

```powershell
python -m pytest tests/test_tidal_handoff_safety.py tests/test_tidal_phase2_closure.py -v
python -m pytest -v
```

## Live validation

First:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --dry-run
```

Then:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal
```

For a run with stale TIDAL state, the destructive reconciliation log must occur
after the Plex playlist update log.

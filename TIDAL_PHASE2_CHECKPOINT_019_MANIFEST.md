# TIDAL Phase 2 — Checkpoint-019

**Date:** 2026-07-23
**Scope:** Timestamped TIDAL matched report + combined Lidarr/TIDAL dispatch validation

## TIDAL matched report

When at least one Plex-unmatched track resolves in TIDAL, PPI writes:

```text
reports/tidal-matched=mmddhhmm.csv
```

using the existing `[reports] directory`.

Schema:

```text
tidal_url,artist,album,track
```

Rows are deduplicated by TIDAL track ID.

No report is created when TIDAL resolves zero tracks.

The report is generated in both dry-run and real runs because it records
catalog resolution only and makes no TIDAL mutation.

TIDAL URLs are derived at report time:

```text
https://tidal.com/browse/track/<track_id>
```

They are not persisted in `tidal_state.db`.

## Combined external dispatch

PPI logs the common post-Plex unmatched pool before external processing:

```text
External unmatched dispatch pool: N track(s); Lidarr=enabled; TIDAL=enabled
```

With `--lidarr-search` or `--lidarr-check`, the same MatchingSession is handed
independently to Lidarr and TIDAL. Lidarr remains asynchronous; TIDAL does not
wait for Lidarr acquisition results.

## Validation

```powershell
python -m pytest tests/test_tidal_reporting.py tests/test_tidal_lidarr_dispatch.py -v
python -m pytest -v
```

Dry report test:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --dry-run
```

With the current Plex library and `allow_explicit=true`, expected current TIDAL
result is approximately one match (`Sublime - What I Got`), producing one CSV row.

Combined dispatch test:

```powershell
python playlist_import_v2.py tidal-test.txt --playlist test-tidal --dry-run --lidarr-search --lidarr-report reports\lidarr_unmatched_report.csv
```

Expected:

```text
External unmatched dispatch pool: 2 track(s); Lidarr=enabled; TIDAL=enabled
```

The two Plex-unmatched source tracks are independently eligible for both
services. TIDAL resolution proceeds without waiting for Lidarr.

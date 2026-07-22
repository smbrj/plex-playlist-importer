# Runtime Architecture

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and Operators  
**Depends On:** configuration.md  
**Related Documents:** cache.md, plex.md, lidarr.md, xmplaylist.md, reporting.md, deployment.md, testing.md  
**Snapshot:** 009

---

# 1. Purpose and Scope

This document describes how the Plex Playlist Importer executes as a running application.

Its purpose is to explain the application lifecycle from process startup through completion, including command-line parsing, configuration loading, logging initialization, runtime mode selection, cache initialization, external-service health checks, search-index loading, input-source resolution, matching, reporting, optional Lidarr processing, Plex playlist modification, analytics, warning/failure behavior, and process exit status.

The primary runtime implementation is:

```text
playlist_import_v2.py
```

Despite the historical filename, the current command-line description identifies the application as:

```text
Plex Playlist Importer V3
```

---

# 2. Runtime Design Principle

The runtime layer coordinates subsystems.

It should not own detailed business logic implemented by those subsystems.

The orchestrator currently coordinates cache, Plex, matcher, reporting, Lidarr, XMPlaylist, station profiles, alias intelligence, analytics, component health, and graceful degradation.

The governing principle remains:

> The runtime orchestrator coordinates subsystem execution while leaving specialized behavior inside the subsystem modules.

---

# 3. Current Runtime Entry Point

The executable script is:

```text
playlist_import_v2.py
```

Normal execution begins in:

```python
main()
```

A user interrupt is caught as `KeyboardInterrupt` and exits with code `1`.

---

# 4. Python Runtime Requirements

The project metadata specifies:

```text
Python >= 3.11
```

Current declared runtime dependencies are:

```text
plexapi
rapidfuzz
requests
tqdm
```

The build system uses:

```text
setuptools >= 69
wheel
```

The project package version is currently `1.0.0`.

---

# 5. Configuration Loading

The current project does not use a separate `config.py` module.

Configuration is loaded directly by the orchestrator through Python `configparser.ConfigParser` using:

```python
load_config(path)
```

The default configuration path is:

```text
config.ini
```

---

# 6. Configuration Responsibilities in the Orchestrator

The orchestrator directly uses configuration to construct or control matching configuration, artist aliases, Plex connection settings, Plex library name, cache database location, cache maximum age, XMPlaylist connection settings and defaults, XMPlaylist state storage, Lidarr configuration, reporting behavior, alias-intelligence storage, and analytics output.

Configuration loading is therefore centralized in the main orchestration layer.

---

# 7. Logging Initialization

Logging is initialized through:

```python
setup_logging()
```

from:

```text
plex_playlist/logging_config.py
```

Current startup order is:

```text
Parse CLI
    |
    v
Resolve XM station profile actions
    |
    v
Initialize Logging
    |
    v
Load config.ini
```

Logging is therefore initialized before the application configuration file is read.

---

# 8. Current Logging Destinations

The current logging implementation writes to:

```text
logs/importer.log
logs/debug.log
logs/runs/<timestamp>.log
```

and also writes to the console.

Directories are created automatically:

```text
logs/
logs/runs/
```

---

# 9. Rotating Logs

The main application log rotates at 5,000,000 bytes with five backups.

The debug log rotates at 20,000,000 bytes with three backups.

A separate per-run DEBUG-level log is also generated.

---

# 10. Logging Configuration Limitation

The current orchestrator calls:

```python
setup_logging()
```

without first reading `[logging] level`.

Log directory, filenames, and rotation values are currently hard-coded.

Existing configuration keys such as `level`, `directory`, and `filename` therefore do not currently control runtime logging.

This discrepancy is part of the post-documentation Configuration Audit.

---

# 11. Runtime Argument Parsing

The application uses `argparse`.

Runtime options cover input-source selection, XMPlaylist profiles, playlist naming, playlist modification mode, cache control, reporting, Lidarr processing, Library Intelligence utilities, and dry-run operation.

The complete CLI reference belongs in the README and built-in help.

---

# 12. Runtime Operating Modes

The runtime supports normal import processing plus several early-exit modes, including profile listing, Library Intelligence operations, and duplicate reporting.

These modes intentionally bypass unnecessary later stages.

---

# 13. XMPlaylist Profile Management

The application supports:

```text
--xmprofile
--all-xmprofiles
--list-xmprofiles
```

Only one profile action may be selected at a time.

The default profile file is:

```text
resources/xmstations.ini
```

Relative profile paths are resolved relative to the selected `config.ini`.

---

# 14. Listing XMPlaylist Profiles

`--list-xmprofiles` loads and prints station profiles, then returns immediately.

No cache initialization, matching, Plex modification, or reporting workflow follows.

---

# 15. Running All XMPlaylist Profiles

`--all-xmprofiles` runs enabled station profiles independently through the station-profile runtime layer.

The resulting profile statuses are combined through:

```text
aggregate_profile_exit_code()
```

---

# 16. Single XMPlaylist Profile

`--xmprofile <name>` retrieves the selected profile, rejects it if disabled, applies profile settings to runtime arguments, and continues through normal execution.

---

# 17. Library Intelligence Early-Exit Mode

The following operations form the Library Intelligence runtime group:

```text
--export-artists
--suggest-aliases
--import-aliases
--audit-aliases
```

If any are requested, they execute after configuration/cache initialization and then return without normal playlist-import processing.

---

# 18. Duplicate Report Early Exit

`--dedupe` loads cached tracks, writes the duplicate report, and returns.

No playlist input or Plex modification is required.

---

# 19. Cache Initialization

The cache database path is read from `[cache] database`, with fallback:

```text
cache/plex_library.db
```

Relative paths are resolved against the directory containing `config.ini`.

The runtime creates `LibraryCache(cache_path)` and calls `cache.initialize()`.

---

# 20. Runtime Health Model

The orchestrator creates:

```python
RunStatus()
```

to track cache, Plex, XMPlaylist, Lidarr, TIDAL, playlist operation, warnings, cache age/track count, cache refresh state, stale Plex matches, and playlist skip reason.

---

# 21. Startup Health Checks

`run_startup_health_checks()` evaluates cache, Plex, XMPlaylist when required, Lidarr, and TIDAL configuration status.

The result is stored in `RunStatus`.

---

# 22. Cache Health

Current cache states are:

```text
EMPTY
STALE
FRESH
```

Cache state uses configured `max_age_hours`, with a built-in fallback of 24 hours.

---

# 23. Plex Startup Health

Plex availability is checked with `plex.is_available()`.

Plex being unavailable at startup does not automatically terminate the run.

Execution may continue if a usable cache exists and the requested operation permits degraded operation.

---

# 24. XMPlaylist Startup Health

XMPlaylist health is checked only when `--xmstation` is active.

For file-based input it is recorded as not required.

---

# 25. Lidarr Startup Health

Lidarr can be available, disabled, not required, or unavailable.

Lidarr is optional and its failure does not invalidate otherwise useful Plex matching work.

---

# 26. TIDAL Runtime State

The orchestrator recognizes a potential `[tidal]` section, but no TIDAL client is currently implemented.

TIDAL remains a planned integration.

---

# 27. Search Index Loading

Normal matching requires a `SearchIndex`.

`load_search_index()` implements normal cached operation, cache refresh, stale-cache fallback, and direct Plex operation through `--no-cache`.

---

# 28. --no-cache Runtime Behavior

When `--no-cache` is selected, Plex must be available.

If Plex is unavailable, a runtime error is raised.

If available, the Plex library is loaded directly and passed to `SearchIndex.build()`.

---

# 29. Cached Runtime Behavior

Normal operation uses the SQLite Plex cache.

A refresh is requested when:

- `--refresh-cache` is supplied.
- The cache is empty.
- The cache is stale.

---

# 30. Cache Refresh with Plex Available

When refresh is needed and Plex is available, the runtime loads the Plex library, replaces cached tracks, marks the cache fresh, and loads the SearchIndex from the cache.

---

# 31. Cache Refresh Failure with Existing Cache

If refresh fails but an existing cache contains tracks, the runtime records a warning and continues with the stale cache.

This is a core graceful-degradation behavior.

---

# 32. Plex Unavailable with Existing Cache

If Plex is unavailable but a cache exists, matching and reporting may continue from stale cache data.

Playlist modification may still be skipped later.

---

# 33. Plex Unavailable with Empty Cache

If Plex is unavailable and no usable cache exists, the run cannot perform Plex-library matching and raises an error.

---

# 34. Input Source Resolution

Exactly one input source must be supplied:

```text
playlist file
```

or:

```text
--xmstation
```

Supplying both or neither raises an error.

---

# 35. File-Based Input Runtime

For file input, `parse_playlist_file()` creates PlaylistEntry objects.

A Plex playlist name is required through `--playlist`.

---

# 36. XMPlaylist Input Runtime

For XMPlaylist input, the runtime calculates effective `history_hours`, `max_requests`, and `max_tracks` from CLI arguments, configuration, and built-in fallbacks.

It validates them before ingestion.

---

# 37. XMPlaylist Partial Backfill

If XMPlaylist ingestion is partial, the runtime logs a warning that the saved cursor will resume backfill on the next run.

Partial history is an expected operational state rather than necessarily a fatal failure.

---

# 38. Matching Runtime

All supported input sources converge on `list[PlaylistEntry]`.

The runtime invokes `run_matcher_entries()`, which calls `match_playlist()` with the entries, SearchIndex, and MatchingConfig.

---

# 39. Report Generation

Reports are generated after matching and before Lidarr processing and Plex playlist modification.

This preserves useful match results even if a later optional integration or playlist operation fails.

---

# 40. Alias Effectiveness Runtime

When enabled, alias usage is recorded in the configured alias-usage SQLite database along with source and playlist context.

---

# 41. Lidarr Runtime

When `--lidarr-check` or `--lidarr-search` is selected, Lidarr processing occurs after primary match reports have been generated.

Lidarr failures are converted into warnings rather than discarding completed matching work.

---

# 42. Lidarr Is Non-Blocking

Lidarr album searches are queued without polling for acquisition completion.

Later runs are expected to observe newly acquired media after normal Lidarr/Plex synchronization.

---

# 43. Dry-Run Runtime

`--dry-run` still performs input acquisition, matching, reporting, alias-effectiveness recording, optional Lidarr processing, analytics, and the run summary.

It does not modify the Plex playlist.

Playlist state becomes:

```text
DRY RUN
```

---

# 44. Dry Run and Lidarr

Dry run does not suppress an explicitly requested `--lidarr-search`.

Lidarr search is a separate explicit external action.

---

# 45. Dry-Run Exit Status

A warning-free dry run returns normally.

A dry run with warnings exits with:

```text
2
```

This allows automation to distinguish clean completion from completion with warnings.

---

# 46. Playlist Mode Resolution

If the run is not a dry run, the runtime selects CREATE, UPDATE, REPLACE, or SYNC.

CREATE is the default.

---

# 47. Plex Availability Before Playlist Modification

Plex availability is checked again immediately before playlist modification.

This allows a run to match from cache while Plex is temporarily unavailable and still attempt modification if Plex later recovers.

---

# 48. Playlist Skip When Plex Is Unavailable

If Plex remains unavailable:

- Playlist modification is skipped.
- Playlist state becomes `SKIPPED`.
- A warning is recorded.
- Analytics are written.
- Run summary is logged.
- The process exits with code `4`.

---

# 49. Resolving Cached Plex Matches

Before modifying a live Plex playlist, cached LibraryTrack matches are resolved back to current Plex objects using `plex.resolve_matches()`.

This identifies stale cached matches that no longer exist in Plex.

---

# 50. Stale Cache with REPLACE or SYNC

For REPLACE and SYNC, stale cached matches are treated as potentially destructive.

The runtime skips playlist modification, records `STALE_PLEX_CACHE`, writes analytics, logs the summary, and exits with code `5`.

---

# 51. Stale Cache with CREATE or UPDATE

For non-destructive modes, valid resolved tracks may continue while stale matches are omitted.

The resulting update completes with warnings.

---

# 52. Plex Resolution Consistency Check

The runtime verifies that resolved tracks plus stale matches equal the expected number of matched tracks.

If the counts disagree, the playlist is skipped, `PLEX_RESOLUTION_MISMATCH` is recorded, and the process exits with code `5`.

---

# 53. Successful Playlist Modification

When Plex is available and cached matches resolve safely, `plex.update_playlist()` is called.

Playlist state becomes `UPDATED` or `UPDATED WITH WARNINGS`.

---

# 54. Runtime Analytics

When analytics are enabled, the runtime records source, playlist, requested/matched/unmatched counts, Lidarr outcomes, runtime duration, cache state, component health, playlist state, and run result.

Default outputs are:

```text
reports/match_analytics.csv
reports/latest_run.json
```

unless overridden.

---

# 55. Run Summary

The runtime logs a structured summary containing cache state, Plex, XMPlaylist, Lidarr, TIDAL, playlist state, stale-cache information, skip reason, and final result.

Final result is shown as `SUCCESS` or `COMPLETED WITH WARNINGS`.

---

# 56. Current Exit Codes

The current explicitly verified runtime exit codes include:

| Exit Code | Meaning |
|---:|---|
| `0` | Normal successful completion through a normal return |
| `1` | Keyboard interruption |
| `2` | Dry run completed with warnings |
| `4` | Plex playlist operation skipped because Plex is unavailable |
| `5` | Playlist skipped because of stale-cache safety or Plex resolution inconsistency |

XMPlaylist multi-profile execution may return an aggregated exit code determined by `aggregate_profile_exit_code()`.

---

# 57. Exceptions and Unhandled Runtime Errors

The top-level entry point only explicitly catches `KeyboardInterrupt`.

Other unhandled exceptions propagate normally, producing a nonzero process status and traceback unless handled inside a subsystem workflow.

---

# 58. Graceful Degradation

The runtime distinguishes component unavailability from total run failure.

Examples:

- Plex unavailable + usable cache → matching may continue.
- Lidarr unavailable → primary Plex matching may continue.
- XMPlaylist unused → not required.
- TIDAL not implemented → not configured.
- Plex unavailable at playlist stage → reports and analytics still survive.

---

# 59. Current Filesystem Runtime Areas

Current runtime areas include:

```text
config.ini
resources/
cache/
reports/
logs/
```

Representative persistent data include Plex cache, Lidarr search history, XMPlaylist state, alias usage, aliases, station profiles, reports, analytics, and logs.

---

# 60. Relative Path Model

Many configured paths are resolved relative to the directory containing `config.ini`.

Current logging paths are instead relative to the process working directory because logging initializes before configuration is loaded.

This distinction is important for future container deployment.

---

# 61. Current Development Runtime

The application currently runs as a headless Python command-line program.

Development and testing have primarily occurred from Windows/PowerShell.

No graphical interface is required.

---

# 62. Headless Design

Primary functionality is available through CLI arguments, INI configuration, filesystem reports, logs, and SQLite state.

This supports unattended operation.

---

# 63. Current Versus Target Deployment

Current runtime:

```text
Python CLI application
```

Target deployment:

```text
Linux container on Unraid
```

Containerization is a target-state feature and belongs in `deployment.md`.

---

# 64. Scheduled Execution

The long-term design calls for cron-style automated execution associated with containerized deployment.

Scheduled container execution is target-state functionality rather than current completed runtime functionality.

The current application is suitable for scheduling because it is headless, uses CLI arguments and exit codes, writes logs/reports, and stores persistent state.

---

# 65. Dashboard Status

The future dashboard is not part of the current runtime.

Current health visibility is provided by RunStatus, logs, analytics, reports, and process exit status.

---

# 66. Runtime Safety Principles

Runtime safety includes:

- Require exactly one input source.
- Require playlist name for file input.
- Reject invalid XMPlaylist limits.
- Require Plex for `--no-cache`.
- Continue with stale cache only when usable.
- Recheck Plex before playlist modification.
- Resolve cached tracks against live Plex.
- Skip REPLACE/SYNC when stale Plex matches exist.
- Skip modification when resolution counts are inconsistent.

These checks favor safe incomplete execution over potentially destructive playlist changes.

---

# 67. Runtime Testing

The project test suite includes runtime/component-health and resiliency coverage.

The later `testing.md` document should inventory tests covering RunStatus, ComponentHealth, cache fallback, Plex unavailable behavior, stale-cache resolution, XMPlaylist profile execution, exit-code behavior, CLI validation, and integration failure isolation.

---

# 68. Post-Documentation Technical Review Candidates

## 68.1 Consider Extracting Configuration Loading

The current orchestrator owns substantial configuration parsing.

A dedicated configuration module could be evaluated if it materially improves maintainability.

The older V2.1 `config.py` should not be restored merely because it previously existed.

## 68.2 Wire Logging to Configuration

Current logging paths, filenames, rotation sizes, and main log levels contain hard-coded operational values.

These should be reviewed under the Configuration Audit.

## 68.3 Resolve Logging Startup Order

If logging becomes configuration-driven, startup order must be reconsidered.

Possible approaches include bootstrap logging or loading configuration before full logger initialization.

## 68.4 Formalize Exit-Code Documentation and Regression Tests

The current exit codes have meaningful operational semantics and should receive explicit regression tests.

At minimum, tests should verify the currently documented codes:

```text
0
1
2
4
5
```

where practical, plus the multi-profile aggregated exit-code behavior.

This is especially important for future scheduled/container operation.

## 68.5 Review Unhandled Exception Policy

A future runtime review should consider whether unattended execution would benefit from consistent fatal-error logging and a defined generic fatal exit code while preserving diagnostic tracebacks.

## 68.6 Review Filename/Version Naming

The entry-point file remains `playlist_import_v2.py` while argparse identifies the application as Plex Playlist Importer V3.

This naming mismatch should be resolved in a later cleanup/release pass.

## 68.7 Validate Multi-Profile Exit-Code Aggregation

`--all-xmprofiles` uses `aggregate_profile_exit_code()`.

The exact mapping from per-profile results to final process exit code should be documented and directly tested.

---

# 69. Future Considerations

Potential future runtime improvements include:

- Linux/Unraid containerization.
- Cron-based scheduled execution.
- Application-health dashboard.
- Configuration-driven logging.
- More formal exit-code specification.
- Cleaner fatal-error handling.
- Startup configuration validation.
- Runtime lock or concurrency protection.
- Structured machine-readable run summaries.
- Container health checks.
- Graceful shutdown handling.
- Consolidation of entry-point naming for the next major version.

Future changes should preserve the guiding rule:

> The runtime should complete as much useful work as safely possible, isolate optional subsystem failures, and avoid destructive playlist changes when system state is uncertain.

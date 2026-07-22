# Technical Cleanup Checkpoint-001

**Date:** 2026-07-22  
**Scope:** Configuration / hard-coded-value audit cleanup

## Changes

### Matching configuration

- Corrected `min_title_score` fallback/default to `95`.
- Corrected `fallback_title_score` fallback/default to `80`.
- Applied the correction in both the CLI configuration builder and `MatchingConfig` model defaults.

### Lidarr configuration

- Standardized Lidarr HTTP timeout default at `20` seconds.
- Wired `remember_failed_searches` into the runtime Lidarr diagnostic/search path.
- Wired `retry_search_after_days` into the runtime retry policy.
- Wired `search_history_database` into `LidarrSearchHistoryStore`.
- Search-history database paths resolve relative to the selected config file.
- Setting `remember_failed_searches = false` disables persistent history consultation/recording for the runtime path.

### Logging configuration

- Logging is now configured after `config.ini` is loaded.
- `[logging] level` controls console logging level.
- `[logging] directory` controls the log directory.
- `[logging] filename` controls the primary rotating application log filename.
- `debug.log` and per-run logs remain under the configured log directory.

### Report configuration

- `[reports] directory`, `match`, `unmatched`, and `lidarr` now define persistent defaults.
- CLI `--report`, `--unmatched`, and `--lidarr-report` remain explicit overrides.
- Match and unmatched CSV writers now create missing parent directories.

### Configuration schema

- `config_version = 3` is now validated at startup.
- Missing configuration files fail clearly.
- Unsupported config versions fail clearly rather than being silently accepted.

### Removed dead/redundant sample configuration

Removed from `config.example.ini`:

- `[cache] enabled`
- `[cache] refresh_on_start`
- `[playlist] duplicates`
- `[playlist] preserve_order`

These values were not consumed by the current runtime and duplicate fixed behavior or explicit CLI controls.

## User config.ini migration

Apply these changes to the real `config.ini`:

```ini
[lidarr]
timeout_seconds = 20
remember_failed_searches = true
retry_search_after_days = 7
search_history_database = cache/lidarr_search_history.db

[cache]
database = cache/plex_library.db
max_age_hours = 12

[reports]
directory = reports
match = playlist_report.csv
unmatched = unmatched.csv
lidarr = lidarr_unmatched_report.csv
include_file_paths = false

[logging]
level = INFO
directory = logs
filename = playlist_import.log
```

Remove `enabled` and `refresh_on_start` from `[cache]` if present.
Remove the obsolete `[playlist]` keys `duplicates` and `preserve_order` if present.

## Verification performed

Targeted regression command:

```text
python -m pytest tests/test_config_cleanup.py tests/test_lidarr_client.py tests/test_lidarr_reporting.py tests/test_lidarr_retry_policy.py tests/test_lidarr_search_history.py tests/test_matcher_smoke.py -q
```

Result:

```text
27 passed
```

Python compilation also passed for:

- `playlist_import_v2.py`
- `plex_playlist/models.py`
- `plex_playlist/logging_config.py`
- `plex_playlist/reporting.py`

## Environment limitation

The uploaded package-source set did not include the production XMPlaylist/XM station-profile modules. Temporary stubs were used only inside the validation workspace so `playlist_import_v2.py` could be imported. Those stubs are NOT included in this checkpoint.

Because CLI report arguments now default through `[reports]`, the full project test suite should be run in the user's actual repository after extraction, with particular attention to `tests/test_xmstation_profiles.py` and the XMPlaylist tests.

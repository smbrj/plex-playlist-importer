# Configuration

**Document Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-07-21  
**Primary Audience:** Developers and operators  
**Depends On:** README.md, subsystem-overview.md  
**Related Documents:** cache.md, plex.md, lidarr.md, xmplaylist.md, aliases.md  
**Snapshot:** 004

---

# 1. Purpose and Scope

This document describes how the Plex Playlist Importer is configured.

Its purpose is to provide a central reference for:

- Application configuration.
- External service connections.
- Matching behavior.
- Cache behavior.
- Reporting and logging.
- Alias processing.
- XMPlaylist ingestion defaults.
- XMPlaylist station-specific preferences.
- Lidarr integration and retry behavior.

The project currently separates configuration into two primary files:

```text
config.ini
resources/xmstations.ini
```

`config.ini` contains system and application configuration.

`resources/xmstations.ini` contains user-defined XMPlaylist station preferences.

This separation keeps general application behavior independent from the collection of SiriusXM channels that the maintainer chooses to import.

---

# 2. Configuration Architecture

The configuration model is divided into application-wide settings and station-specific settings.

```text
Plex Playlist Importer
        |
        +-----------------------------+
        |                             |
        v                             v
    config.ini                resources/xmstations.ini
        |                             |
        v                             v
Application / System            XMPlaylist Station
Configuration                   Preferences
        |                             |
        +-------------+---------------+
                      |
                      v
             Runtime Configuration
                      |
                      v
              Importer Workflow
```

`config.ini` defines the normal operating environment of the application.

`resources/xmstations.ini` defines individual XMPlaylist station profiles and allows station-specific values to specialize XMPlaylist behavior.

---

# 3. Configuration Sources and Precedence

Configuration may come from several sources:

```text
Built-in Application Fallbacks
        |
        v
config.ini
        |
        v
XMPlaylist Station Profile
(resources/xmstations.ini)
        |
        v
Explicit CLI Arguments
        |
        v
Effective Runtime Configuration
```

The general principle is that more specific runtime instructions take precedence over broader defaults.

For direct XMPlaylist execution, the current implementation explicitly applies:

```text
CLI value
   |
   | if supplied
   v
config.ini value
   |
   | if present
   v
built-in fallback
```

This behavior is currently verified for:

- `--xmhours`
- `--xm-max-requests`
- `--xm-max-tracks`

For station-profile execution, the selected profile is applied to the runtime argument structure before normal execution proceeds.

The profile mechanism therefore acts as a persistent set of station-specific runtime preferences.

The exact mapping of every profile field is implemented by the XMPlaylist station-profile layer.

---

# 4. Configured Values Versus Built-In Fallbacks

A configured value and a built-in fallback are not the same thing.

The current application includes built-in fallback values that are used when the corresponding persistent configuration value is missing.

Representative examples include:

| Setting | Current Configured Value | Built-in Fallback |
|---|---:|---:|
| XMPlaylist history window | 168 hours | 8 hours |
| XMPlaylist max requests | 8 | 10 |
| XMPlaylist max tracks | 100 | Unlimited if unset |
| Plex cache maximum age | 12 hours | 24 hours |
| Lidarr timeout | 60 seconds | 20 seconds |

The configured value represents the current operating preference.

The built-in fallback provides safe behavior when the configuration value is absent.

Documentation should distinguish between the two.

---

# 5. Configuration Version

The current configuration schema identifies itself using:

```ini
[application]

config_version = 3
```

The configuration version provides a mechanism for distinguishing configuration schemas over time.

The current reviewed orchestrator loads this setting as part of `config.ini`, but no automatic configuration migration behavior has been verified in the current code.

The value should therefore be treated as a schema identifier rather than as evidence of an implemented migration system.

---

# 6. Plex Configuration

Plex connectivity is defined in:

```ini
[plex]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `url` | Base URL of the Plex Media Server |
| `token` | Plex authentication token |
| `library` | Name of the Plex music library |

Example:

```ini
[plex]

url = http://plex-server:32400
token = PLEX-TOKEN-HERE
library = Music
```

The configured library identifies the Plex music library used by the importer.

The Plex token is sensitive and should not be:

- Logged.
- Written to reports.
- Included in documentation.
- Committed to a public repository.
- Included in troubleshooting output without redaction.

See `plex.md` for Plex subsystem behavior.

---

# 7. Lidarr Configuration

Lidarr integration is configured in:

```ini
[lidarr]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `enabled` | Enables or disables Lidarr integration |
| `url` | Base URL of the Lidarr server |
| `api_key` | Lidarr API authentication key |
| `remember_failed_searches` | Retains prior failed searches for retry decisions |
| `retry_search_after_days` | Minimum retry interval for eligible prior searches |
| `search_history_database` | SQLite database containing Lidarr search history |
| `timeout_seconds` | HTTP timeout for Lidarr API requests |

Example:

```ini
[lidarr]

enabled = true
url = http://lidarr-server:8686
api_key = LIDARR_API_KEY_HERE

remember_failed_searches = true
retry_search_after_days = 7
search_history_database = cache/lidarr_search_history.db

timeout_seconds = 60
```

The current orchestrator directly consumes:

- `enabled`
- `url`
- `api_key`
- `timeout_seconds`

The retry and history settings are used by the Lidarr search-history and retry-policy implementation.

Lidarr search history is persistent operational state.

The API key is sensitive and should be protected using the same practices applied to the Plex token.

See `lidarr.md` for the complete Lidarr processing model.

---

# 8. XMPlaylist Configuration

Application-wide XMPlaylist defaults are configured in:

```ini
[xmplaylist]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `base_url` | XMPlaylist service base URL |
| `timeout_seconds` | HTTP timeout for XMPlaylist requests |
| `user_agent` | User-Agent supplied by the importer |
| `state_database` | SQLite database used for XMPlaylist history and state |
| `history_hours` | Default rolling history window |
| `max_requests_per_run` | Maximum XMPlaylist API requests allowed during one importer run |
| `max_tracks_per_run` | Maximum unique-track target for one importer run |

Example:

```ini
[xmplaylist]

base_url = https://xmplaylist.com
timeout_seconds = 20
user_agent = plex-playlist-importer/1.0

state_database = cache/xmplaylist_history.db
history_hours = 168
max_requests_per_run = 8
max_tracks_per_run = 100
```

`history_hours` is measured in hours.

For example:

```text
168 hours = 7 days
```

The importer validates the history window as:

```text
1 through 720 hours
```

The request budget must be at least:

```text
2 requests
```

because station resolution consumes one request and history retrieval requires at least one additional request.

The importer-level `max_requests_per_run` is separate from any external XMPlaylist service quota.

The external account or service quota is controlled by XMPlaylist.

`max_requests_per_run` is an application control intended to limit how much of that external quota one execution may consume.

---

# 9. XMPlaylist Station Configuration

XMPlaylist station preferences are maintained in:

```text
resources/xmstations.ini
```

Each INI section represents a named station profile.

For example:

```ini
[the_bridge]

channel = 14
playlist = default
history_hours = 168
max_tracks = 100
max_requests = 8
mode = update
lidarr_check = false
lidarr_search = true
enabled = true
```

Additional representative profile names include:

```text
70_on_7
yacht_rock
301_roadtrip
```

The section name is a user-defined profile identifier.

It does not determine the SiriusXM channel number.

The `channel` setting provides the actual XMPlaylist/SiriusXM channel number.

The current CLI profile controls include:

```text
--xmprofile
--all-xmprofiles
--list-xmprofiles
--xmstations-file
```

The default station-profile file is:

```text
resources/xmstations.ini
```

---

# 10. XMPlaylist Station Settings

Each station profile may contain:

| Setting | Purpose |
|---|---|
| `channel` | SiriusXM/XMPlaylist channel number |
| `playlist` | Plex playlist name or `default` |
| `history_hours` | Rolling history window for the station |
| `max_tracks` | Maximum unique-track target for the station |
| `max_requests` | Maximum XMPlaylist requests for the station run |
| `mode` | Playlist operation mode |
| `lidarr_check` | Enables Lidarr investigation for unmatched tracks |
| `lidarr_search` | Enables active Lidarr searches for unmatched tracks |
| `enabled` | Enables or disables the profile |

Station-profile names intentionally differ slightly from the global XMPlaylist configuration keys:

```text
config.ini                  xmstations.ini
------------------------------------------------
history_hours               history_hours
max_tracks_per_run          max_tracks
max_requests_per_run        max_requests
```

The global values provide application defaults.

The profile values provide station-specific preferences.

The selected profile is applied to the runtime argument structure before normal execution.

---

# 11. XMPlaylist Playlist Naming

The station configuration supports:

```ini
playlist = default
```

When `default` is used, the playlist name follows:

```text
Ch <channel> - <XMPlaylist station name>
```

Example:

```text
Ch 14 - The Bridge
```

The XMPlaylist client confirms this naming convention when resolving a channel.

A custom playlist name may also be configured:

```ini
playlist = Mike's Classic Vinyl
```

---

# 12. Playlist Modes

The application supports four playlist modes:

```text
create
update
replace
sync
```

At the CLI level:

- `CREATE` is the default.
- `--update`
- `--replace`
- `--sync`

are mutually exclusive.

Current behavior is:

| Mode | Current Behavior |
|---|---|
| `create` | Creates the playlist if it does not exist. If a playlist with the same name already exists, the create operation does not silently overwrite it. |
| `update` | Preserves existing playlist items and adds requested tracks that are not already present. |
| `replace` | Removes the existing playlist contents and replaces them with the requested tracks. |
| `sync` | Currently follows the same additive behavior as `update`. It does not currently remove playlist entries that are absent from the requested source. |

The current implementation should therefore not be interpreted as providing a destructive full synchronization when `sync` is selected.

This distinction should be revisited during the post-documentation technical cleanup phase.

---

# 13. Enabling and Disabling Station Profiles

Each station profile contains:

```ini
enabled = true
```

or:

```ini
enabled = false
```

A disabled profile remains in the file but is excluded from normal profile execution.

This is useful for:

- Temporarily disabling a station.
- Preserving experimental profiles.
- Keeping example profiles.
- Preparing future station definitions.

When an explicitly selected profile is disabled, the current orchestration rejects the run rather than silently executing it.

---

# 14. Station-Specific Lidarr Behavior

Each XMPlaylist station profile may independently specify:

```ini
lidarr_check = false
lidarr_search = true
```

This allows station profiles to define whether unmatched tracks should proceed to Lidarr investigation or active Lidarr search.

`lidarr_search` is operationally significant because it may cause real Lidarr album-search requests.

The distinction remains:

```text
lidarr_check
    |
    v
Read-only investigation

lidarr_search
    |
    v
May submit album searches
```

See `lidarr.md` for detailed behavior.

---

# 15. XMPlaylist State and Backfill Behavior

The XMPlaylist state database is configured using:

```ini
state_database = cache/xmplaylist_history.db
```

The current implementation supports persistent backfill state.

If an execution stops before completing the requested history window because the request budget is exhausted, the saved cursor may be used on the next run to continue retrieval.

Changing the configured history window resets saved state associated with the earlier window.

This avoids mixing backfill state created under different history-window requirements.

---

# 16. Analytics Configuration

Analytics behavior is configured in:

```ini
[analytics]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `enabled` | Enables analytics collection |
| `history_csv` | Historical analytics CSV output |
| `latest_json` | JSON summary of the latest run |

Example:

```ini
[analytics]

enabled = true
history_csv = reports/match_analytics.csv
latest_json = reports/latest_run.json
```

The current orchestrator consumes these settings.

Relative analytics paths are resolved relative to the directory containing the selected `config.ini`.

Detailed analytics behavior belongs in `analytics.md`.

---

# 17. Alias Intelligence Configuration

Alias intelligence is configured in:

```ini
[alias_intelligence]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `track_usage` | Enables alias usage tracking |
| `usage_database` | SQLite database containing alias usage information |
| `review_after_days` | Age threshold used when evaluating aliases for review |

Example:

```ini
[alias_intelligence]

track_usage = true
usage_database = cache/alias_usage.db
review_after_days = 90
```

Relative database paths are resolved relative to the directory containing `config.ini`.

See `aliases.md` for alias behavior and alias-intelligence architecture.

---

# 18. Matching Configuration

Matching behavior is configured in:

```ini
[matching]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `threshold` | Minimum acceptable overall match score |
| `threads` | Number of matching worker threads |
| `preferred_versions` | Preferred recording types in descending priority |
| `artist_weight` | Artist contribution to weighted scoring |
| `album_artist_weight` | Album artist contribution |
| `title_weight` | Track-title contribution |
| `combined_weight` | Combined normalized comparison contribution |
| `min_title_score` | Title-score constraint used by matching logic |
| `fallback_title_score` | Title threshold used by fallback matching behavior |

Current scoring weights are:

```text
Artist          0.25
Album Artist    0.15
Title           0.45
Combined        0.15
                ----
Total           1.00
```

Current configured threshold:

```ini
threshold = 85
```

Current preferred-version ordering:

```ini
preferred_versions = studio,remaster,stereo,album,single,live,acoustic,demo,alternate,instrumental,radio,extended,edit,mono
```

The current orchestrator directly builds `MatchingConfig` from these settings.

See `matching.md` for detailed matching behavior.

---

# 19. Cache Configuration

Plex library caching is configured in:

```ini
[cache]
```

Current configuration contains:

| Setting | Current Status |
|---|---|
| `enabled` | Present in `config.ini`; not currently consumed by the reviewed main orchestration path |
| `database` | Actively consumed |
| `refresh_on_start` | Present in `config.ini`; not currently consumed by the reviewed main orchestration path |
| `max_age_hours` | Actively consumed |

Example:

```ini
[cache]

enabled = true
database = cache/plex_library.db
refresh_on_start = false
max_age_hours = 12
```

Current cache behavior is controlled primarily through:

```text
normal cached operation
--refresh-cache
--no-cache
```

The cache database path is resolved relative to the directory containing the selected `config.ini`, unless an absolute path is configured.

The application automatically considers cache age when determining whether a refresh is needed.

The currently configured cache-age limit is:

```text
12 hours
```

The built-in fallback is:

```text
24 hours
```

The unused `enabled` and `refresh_on_start` settings should be evaluated during the post-documentation Configuration Audit.

See `cache.md` for full cache behavior.

---

# 20. Reports Configuration

Report-related configuration currently includes:

```ini
[reports]

unmatched = unmatched.csv
output_path = reports/
include_file_paths = false
```

Current runtime status is:

| Setting | Current Status |
|---|---|
| `include_file_paths` | Actively consumed by the orchestrator |
| `unmatched` | Present in `config.ini`, but not currently used by the main CLI report-path logic |
| `output_path` | Present in `config.ini`, but not currently used by the main CLI report-path logic |

Current CLI defaults provide report destinations such as:

```text
--unmatched
--report
--lidarr-report
```

Therefore, `unmatched` and `output_path` should not currently be documented as authoritative report-path controls.

The current configuration also contains:

```ini
#path = reports/
```

which is commented and has no runtime effect.

The report-path configuration should be reviewed during the post-documentation Configuration Audit.

---

# 21. Artist Alias Configuration

Static artist aliases are configured in:

```ini
[artist_aliases]
```

Current settings are:

| Setting | Purpose |
|---|---|
| `enabled` | Enables artist alias processing |
| `file` | Path to the alias definition file |

Example:

```ini
[artist_aliases]

enabled = true
file = resources/aliases.txt
```

The alias file path is resolved relative to the directory containing the selected `config.ini`, unless an absolute path is supplied.

See `aliases.md` for alias processing behavior.

---

# 22. Logging Configuration

The current configuration contains:

```ini
[logging]

debug = false
trace = false
level = INFO
directory = logs
filename = playlist_import.log
```

These settings do not all currently control the same subsystem.

## Active Matching Diagnostic Settings

The orchestrator reads:

```text
debug
trace
```

and passes them into `MatchingConfig`.

Their intended meanings are:

```text
debug=true
    |
    v
candidate / score diagnostics

trace=true
    |
    v
pipeline / timing diagnostics
```

## Logging Settings Present but Not Currently Wired

The following settings exist in `config.ini`:

```text
level
directory
filename
```

but the reviewed current logging setup does not consume them.

The current logging implementation uses its own hard-coded logging paths and filenames.

Therefore, these keys should not presently be interpreted as controlling actual log destinations or log level.

This discrepancy is a priority item for the post-documentation Configuration Audit.

---

# 23. Playlist Configuration

The current `config.ini` contains:

```ini
[playlist]

duplicates = skip
preserve_order = true
```

These settings express intended playlist behavior, but their runtime consumption was not identified in the reviewed main orchestration and Plex playlist-management paths.

They should therefore be documented as:

> Present in the current configuration schema, but not yet verified as active runtime controls in the reviewed implementation.

The application does preserve source-order behavior in several processing areas, but that should not be attributed specifically to `preserve_order = true` until direct configuration consumption is verified.

Similarly, duplicate behavior should not be attributed specifically to `duplicates = skip` without verified consumption.

These settings should be included in the post-documentation Configuration Audit.

---

# 24. CLI Overrides and Runtime Controls

The application exposes runtime options including:

```text
--config
--refresh-cache
--no-cache
--lidarr-check
--lidarr-search
--lidarr-report
--dry-run

--xmstation
--xmhours
--xm-max-requests
--xm-max-tracks

--xmprofile
--all-xmprofiles
--list-xmprofiles
--xmstations-file
```

For direct XMPlaylist operation, the current implementation explicitly gives CLI values precedence over the corresponding `[xmplaylist]` values.

Examples:

```text
--xmhours
    overrides
[xmplaylist] history_hours
```

```text
--xm-max-requests
    overrides
[xmplaylist] max_requests_per_run
```

```text
--xm-max-tracks
    overrides
[xmplaylist] max_tracks_per_run
```

CLI arguments apply only to the current execution.

They do not modify `config.ini` or `resources/xmstations.ini`.

The full CLI reference should remain in README/CLI help rather than being duplicated here.

---

# 25. Sensitive Configuration Values

The current configuration contains two primary sensitive credential types:

```text
Plex authentication token
Lidarr API key
```

These values should not be:

- Logged.
- Included in reports.
- Included in documentation.
- Included in screenshots.
- Committed to public repositories.
- Included in troubleshooting output without redaction.

Documentation and sample configuration should use placeholders such as:

```text
PLEX-TOKEN-HERE
LIDARR_API_KEY_HERE
```

---

# 26. Paths and Relative-Path Behavior

Several configuration paths are explicitly resolved relative to the directory containing the selected `config.ini`.

Verified examples include:

```text
cache/plex_library.db
cache/xmplaylist_history.db
cache/alias_usage.db
resources/aliases.txt
reports/match_analytics.csv
reports/latest_run.json
```

This behavior improves portability because configuration can move with the project or deployment environment.

Absolute paths remain supported where implemented.

The project should avoid unnecessary Windows-specific absolute paths because the final deployment target is Linux/Unraid.

---

# 27. Container Deployment Considerations

The long-term deployment target is a Linux-based container hosted on an Unraid server.

Configuration should distinguish among:

```text
Configuration
     |
     v
Persistent configuration storage

Operational state
     |
     v
Persistent database storage

Generated output
     |
     v
Reports and logs
```

Persistent operational databases include:

```text
cache/lidarr_search_history.db
cache/xmplaylist_history.db
cache/alias_usage.db
```

The Plex library cache is reproducible from Plex, but persistence is still desirable for performance and degraded-mode operation.

Container volume mappings will be documented in `deployment.md`.

---

# 28. Configuration Validation and Failure Behavior

The current implementation performs several explicit validations.

Examples include:

```text
XMPlaylist history_hours
    must be between 1 and 720
```

```text
XMPlaylist max_requests
    must be at least 2
```

```text
XMPlaylist max_tracks
    if configured, must be at least 1
```

```text
Lidarr timeout_seconds
    must be greater than 0
```

Missing or invalid subsystem configuration should be attributed to the affected component whenever practical.

Examples:

```text
Invalid Plex configuration
        |
        v
Plex unavailable
```

```text
Invalid Lidarr configuration
        |
        v
Lidarr unavailable
```

```text
Invalid XMPlaylist configuration
        |
        v
XMPlaylist ingestion unavailable
```

Optional integration failures should remain isolated where possible.

Sensitive configuration values should not be included in errors or diagnostic output.

---

# 29. Operational Troubleshooting

When troubleshooting configuration:

1. Confirm the intended `config.ini` is being loaded.
2. Confirm the expected `config_version`.
3. Identify the affected subsystem.
4. Verify that the relevant INI section exists.
5. Verify required settings.
6. Check whether the setting is actively consumed by the current implementation.
7. Verify relative paths against the directory containing the selected `config.ini`.
8. Confirm external service URLs.
9. Confirm credentials without exposing them.
10. Review CLI options that may override persistent configuration.
11. For XMPlaylist profile execution, review both `[xmplaylist]` and the selected station profile.
12. Confirm the station profile is enabled.
13. Review application logs for the effective failure point.

Configuration troubleshooting should begin with the smallest affected subsystem rather than assuming a global application failure.

---

# 30. Testing

Configuration-related behavior is currently exercised through application and subsystem tests rather than through a single dedicated configuration test suite.

Verified XMPlaylist test coverage includes:

- Request-budget enforcement.
- Rejection of request budgets below two.
- History-window validation.
- Persistent cursor/backfill continuation.
- Resetting saved state after a history-window change.
- Station resolution.
- Playlist-name generation.
- History-page and cursor parsing.
- HTTP 429 rate-limit reporting.

Representative command:

```bash
python -m pytest tests/test_xmplaylist_client.py tests/test_xmplaylist_source.py -v
```

Before significant configuration changes:

```bash
python -m pytest -v
```

Future configuration-specific tests should cover:

- Required sections.
- Defaults and fallbacks.
- Config-version compatibility.
- Boolean and numeric parsing.
- CLI/config precedence.
- Station-profile mapping.
- Relative-path behavior.
- Deprecated or unused settings.
- Configuration-health diagnostics.

---

# 31. ADR References

## ADR-003 — Embedded SQLite for Local Persistence

Configuration identifies SQLite databases used for Plex caching, Lidarr search history, XMPlaylist state, and alias usage.

## ADR-007 — Isolate Optional Integration Failures

Configuration problems affecting optional integrations should not unnecessarily invalidate unrelated application work.

## ADR-009 — Headless Containerized Deployment

Configuration and data paths must remain compatible with Linux-based container deployment on Unraid.

---

# 32. Post-Documentation Configuration Audit

The documentation review has identified configuration drift between some INI settings and the current implementation.

These findings should be resolved after the documentation baseline is complete.

The Configuration Audit should examine both directions.

## 32.1 Hard-Coded Operational Values

Review the application for hard-coded operational values such as:

- Paths.
- Filenames.
- Timeouts.
- Retry intervals.
- Request limits.
- Cache ages.
- Logging behavior.
- Operational thresholds.

For each value:

```text
Hard-coded operational value
        |
        v
Should the maintainer reasonably control it?
        |
   +----+----+
   |         |
  Yes        No
   |         |
   v         v
Add or use   Keep as
config.ini   internal
setting      constant
   |
   v
Retain a sensible
code fallback
```

Not every internal constant should become configurable.

Only values that provide meaningful operational or deployment control should be exposed.

## 32.2 Existing Configuration Keys

Review every existing INI key to determine whether the application actually consumes it.

```text
Existing config.ini key
        |
        v
Used by current implementation?
        |
   +----+----+
   |         |
  Yes        No
   |         |
   v         v
Verify       Wire into
behavior     implementation
             or deprecate/remove
```

Current known audit candidates include:

```text
[cache]
enabled
refresh_on_start

[reports]
unmatched
output_path

[logging]
level
directory
filename

[playlist]
duplicates
preserve_order
```

The playlist `sync` behavior should also be reviewed because it currently behaves like `update`.

The audit should occur after the documentation phase so that the documentation first establishes an accurate baseline of current application behavior.

---

# 33. Future Considerations

Potential future improvements include:

- Formal configuration schema validation.
- Automatic configuration-version migration.
- Environment-variable support for credentials.
- Container-native secret management.
- Startup validation with actionable errors.
- Sanitized effective-configuration reporting.
- Better visibility into configuration precedence.
- Detection of obsolete or unused configuration keys.
- Maintained sample configuration files.
- Configuration-health visibility in the operational dashboard.
- Full completion of the post-documentation Configuration Audit.

The guiding principle is:

> Configuration should expose meaningful operational choices without turning every internal implementation constant into a user-facing setting.

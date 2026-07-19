# Subsystem Overview

## 1. Purpose

This document is the high-level map of Plex Playlist Importer subsystems and their implementation relationships.

It identifies the purpose of each subsystem, primary modules, callers/dependencies, persistent stores/resources, and primary pytest coverage.

Detailed processing behavior belongs in individual subsystem documents.

## 2. High-Level Subsystem Map

```text
                         playlist_import_v2.py
                         Application Orchestration
                                  |
          +-----------------------+-----------------------+
          |                       |                       |
          v                       v                       v
   Playlist Parsing          XMPlaylist Source       Plex Cache
     parser.py              xmplaylist_source.py      cache.py
          |                       |                       |
          v                       v                       v
      models.py                 models.py             SearchIndex
          |                       |                  search_index.py
          +-----------+-----------+                       |
                      |                                   |
                      v                                   |
                PlaylistEntry                             |
                      |                                   |
                      +---------------+-------------------+
                                      |
                                      v
                               Matching Subsystem
                                  matcher.py
                               normalization.py
                               search_index.py
                                      |
                                      v
                                MatchingSession
                                  MatchResult
                                  models.py
                                      |
                  +-------------------+-------------------+
                  |                                       |
                  v                                       v
           Matched Results                         Unmatched Results
                  |                                       |
                  v                                       v
             Plex Client                          Lidarr Integration
           plex_client.py                         lidarr_reporting.py
                  |                               lidarr_acquisition.py
                  v                               lidarr_client.py
             Plex Server                          lidarr_search_history.py
                                                          |
                                                          v
                                                     Lidarr Server

Supporting subsystems:

resources.py
    -> loads resources/aliases.txt

alias_usage.py
    -> records post-match alias usage
    -> cache/alias_usage.db

alias_intelligence.py
    -> alias discovery, suggestions, import, and audit

reporting.py
    -> match, unmatched, duplicate reports

analytics.py
    -> run analytics and latest-run status

runtime.py
    -> component health and run status

logging_config.py
    -> application logging configuration
```

## 3. Subsystem Relationships and Primary Tests

| Subsystem | Primary Modules | Called By / Used By | Calls / Depends On | Primary pytest coverage |
|---|---|---|---|---|
| Application Orchestration | `playlist_import_v2.py` | CLI invocation | All major subsystems | Full-suite integration through subsystem tests |
| Playlist Parsing | `parser.py` | `playlist_import_v2.py` | `models.py` | `tests/test_parser.py` |
| Matching | `matcher.py`, `normalization.py`, `search_index.py` | `playlist_import_v2.py` | `models.py`; aliases via `MatchingConfig` | `tests/test_matcher_smoke.py` |
| Plex Library Cache | `cache.py` | `playlist_import_v2.py` | `models.py`, `normalization.py`, `search_index.py`, SQLite | `tests/test_cache_resiliency.py` |
| Plex Integration | `plex_client.py` | `playlist_import_v2.py` | Plex API, `runtime.py` | `tests/test_component_health.py`, `tests/test_plex_stale_resolution.py` |
| Artist Alias Loading | `resources.py` | `playlist_import_v2.py` | `resources/aliases.txt` | Alias path exercised by `tests/test_matcher_smoke.py` |
| Alias Usage Tracking | `alias_usage.py` | `playlist_import_v2.py`, `alias_intelligence.py` | `cache/alias_usage.db` | `tests/test_alias_usage.py` |
| Alias Intelligence | `alias_intelligence.py` | Intelligence CLI commands | `alias_usage.py`, `resources/aliases.txt`, Plex cache data | `tests/test_alias_intelligence.py` |
| Lidarr Integration | `lidarr_client.py`, `lidarr_acquisition.py`, `lidarr_reporting.py`, `lidarr_search_history.py` | `playlist_import_v2.py` | Lidarr API, SQLite | `tests/test_lidarr_client.py`, `tests/test_lidarr_reporting.py`, `tests/test_lidarr_retry_policy.py`, `tests/test_lidarr_search_history.py`, compatibility/resilience tests |
| XMPlaylist Integration | `xmplaylist_client.py`, `xmplaylist_source.py`, `xmplaylist_state.py`, `xmstation_profiles.py` | `playlist_import_v2.py` | XMPlaylist API, SQLite, `resources/xmstations.ini` | `tests/test_xmplaylist_client.py`, `tests/test_xmplaylist_source.py`, `tests/test_xmplaylist_state.py`, `tests/test_xmplaylist_max_tracks.py`, `tests/test_xmstation_profiles.py`, health test |
| Reporting | `reporting.py`, `lidarr_reporting.py` | `playlist_import_v2.py` | `models.py`, Lidarr subsystem | `tests/test_lidarr_reporting.py`; match reporting covered through workflow tests |
| Analytics | `analytics.py` | `playlist_import_v2.py` | Generated analytics/status files | `tests/test_analytics.py`, `tests/test_stale_analytics.py` |
| Runtime Health | `runtime.py` | Main workflow and clients | Component state | `tests/test_runtime_health.py`, `tests/test_component_health.py`, `tests/test_xmplaylist_health.py` |
| Logging | `logging_config.py` | `playlist_import_v2.py` | Python logging | Observed through integration tests; no dedicated test file in recorded suite |
| Exceptions | `exceptions.py` | Integration/application modules | None | Exercised through relevant subsystem failure tests |

## 4. Persistent Databases

### Plex Library Cache

`cache/plex_library.db`

Owned by `cache.py`.

Tables:

- `metadata`
- `tracks`

### Artist Alias Usage

`cache/alias_usage.db`

Owned by `alias_usage.py`.

Tables:

- `metadata`
- `alias_usage`

### Lidarr Search History

`cache/lidarr_search_history.db`

Owned by `lidarr_search_history.py`.

Tables:

- `metadata`
- `search_history`

### XMPlaylist History and State

`cache/xmplaylist_history.db`

Owned by `xmplaylist_state.py`.

Tables:

- `metadata`
- `station_state`
- `tracks`

## 5. Configuration and Resource Files

### Main Configuration

`config.ini`

Loaded/interpreted by `playlist_import_v2.py`; subsystem-specific settings are passed into the owning components.

### Artist Alias Definitions

`resources/aliases.txt`

Loaded by `resources.py -> load_artist_aliases()`.

Used by `MatchingConfig.artist_aliases`, `matcher.py`, and alias intelligence.

### XMPlaylist Station Profiles

`resources/xmstations.ini`

Processed by `xmstation_profiles.py`.

## 6. Alias Responsibility Boundary

### Live Alias Matching

```text
resources/aliases.txt
        |
        v
resources.py
load_artist_aliases()
        |
        v
MatchingConfig
(models.py)
        |
        v
matcher.py
```

### Alias Usage Tracking

```text
MatchingSession.results
        |
        v
playlist_import_v2.py
record_alias_effectiveness()
        |
        v
alias_usage.py
count_alias_usage()
AliasUsageStore
        |
        v
cache/alias_usage.db
```

### Alias Intelligence

```text
Plex Library Tracks
        +
resources/aliases.txt
        +
cache/alias_usage.db
        |
        v
alias_intelligence.py
        |
        +--> Export Plex artists
        +--> Suggest aliases
        +--> Import approved aliases
        +--> Audit aliases
```

## 7. Test Inventory Note

The current uploaded code baseline ZIP does not contain the `tests/` directory. The test mappings above are based on the most recent recorded full pytest run, which collected 75 tests and passed all 75.

When a future source snapshot includes the tests themselves, this overview should be verified against the actual `tests/` directory before release.

## 8. Documentation Boundary

`subsystem-overview.md` is the authoritative map of inter-subsystem relationships.

Individual subsystem documents explain internal processing flows and should name actual modules, functions, resources, databases, tables, and relevant pytest files where they participate.

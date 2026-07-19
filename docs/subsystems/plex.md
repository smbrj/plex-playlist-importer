# Plex Integration Subsystem

## 1. Purpose and Scope

The Plex integration subsystem provides the application's interface to the live Plex server and music library. Plex is authoritative for live media objects and Plex playlists.

The governing decision is `ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority`.

## 2. Responsibilities

The subsystem handles Plex connection/authentication, configured library selection, metadata retrieval for cache refresh, live-object resolution, playlist creation/update, and Plex component health.

## 3. Processing Flows

### 3.1 Plex Connection and Library Access

```text
Application Startup / Plex Operation Required
playlist_import_v2.py
        |
        v
Plex Configuration
[Plex] (config.ini)
        |
        +-- Server URL
        +-- Authentication token
        +-- Music library name
        |
        v
PlexClient (plex_client.py)
        |
        v
Connect / Authenticate / Locate Library
        |
        +------------------+
        |                  |
        v                  v
Available             Failure
                       |
                       v
                  runtime.py
```

### 3.2 Plex Library Retrieval for Cache Refresh

```text
Manual Refresh Requested                 Cache Age Evaluation
--refresh-cache                          max_age_hours
(playlist_import_v2.py)                  [cache] (config.ini)
        |                                      |
        |                                      v
        |                               Cache Is Stale?
        |                                      |
        |                                    Yes
        |                                      |
        +------------------+-------------------+
                           |
                           v
                  Cache Refresh Required
                           |
                           v
                     PlexClient
                   (plex_client.py)
                           |
                           v
                  Live Plex Music Library
                           |
                           v
                 Retrieve Track Metadata
                           |
                           v
                    cache.py
                           |
                           v
                 cache/plex_library.db
```

A refresh can be initiated explicitly with `--refresh-cache` or automatically when the cache exceeds `max_age_hours`. Plex retrieves authoritative live data; the cache subsystem owns persistence.

### 3.3 Cached Match to Live Plex Resolution

```text
Successful Cached Match
        |
        v
Cached Plex Track Identity
        |
        v
PlexClient (plex_client.py)
        |
        +------------------+
        |                  |
        v                  v
Resolved             Not Found
        |                  |
        v                  v
Plex Operation       Stale Cache Identity
```

### 3.4 Plex Playlist Modification

```text
Resolved Live Plex Tracks
        |
        v
Playlist Requested
--playlist
        |
        v
Dry Run Enabled?
--dry-run
        |
   +----+----+
   |         |
  Yes        No
   |         |
   v         v
Skip Plex    Locate Existing Playlist
Write             |
                  +-------------+
                  |             |
                  v             v
                Update        Create
                  |             |
                  +------+------+
                         |
                         v
                   Live Plex Server
```

`--dry-run` prevents Plex playlist modification. It does not globally disable explicitly requested live operations in other subsystems.

## 4. Plex Configuration

Plex-related settings in `config.ini` identify the server, authentication token, and music library. Exact setting documentation belongs in `docs/configuration.md`.

## 5. Plex Authentication

The Plex token is a secret and must not be exposed in logs, reports, examples, or public repositories.

## 6. Plex Library Selection

Failure to locate the configured library is a configuration/availability failure, not an empty library.

## 7. Library Metadata Retrieval

The Plex subsystem retrieves the metadata needed to construct application `Track` models for matching, identity resolution, and playlist operations.

## 8. Live Plex Resolution

Cached metadata is not a live Plex object. Cached identities must resolve to live Plex objects before playlist modification.

## 9. Playlist Creation and Update

The application determines which tracks belong in the playlist; the Plex subsystem performs the requested live Plex operation.

## 10. Playlist Order

The Plex subsystem preserves the order supplied by the application workflow.

## 11. Duplicate Handling

Representative configuration:

```ini
[playlist]
duplicates=skip
```

Playlist duplicate policy remains distinct from source-level deduplication.

## 12. Dry-Run Semantics

`--dry-run` applies specifically to Plex playlist modification. Parsing, matching, reports, and explicitly requested external operations may still occur.

## 13. Plex Unavailability

If Plex is unavailable but a usable cache exists, safe cache-backed work may continue. Requested Plex playlist modification must be skipped and the run should not be reported as complete success.

## 14. Component Health

Plex health is reflected through `runtime.py`, distinguishing healthy, unavailable-but-degraded-work-possible, and unavailable-and-requested-operation-blocked states.

## 15. Failure Behavior

Connection, authentication, library selection, live resolution, and playlist modification failures should be reported distinctly.

## 16. Logging and Observability

Logs should make Plex connection, library access, metadata retrieval, live resolution, playlist action, dry-run suppression, and degraded operation understandable without exposing credentials.

## 17. Testing

Primary coverage:
- `tests/test_plex_stale_resolution.py`
- `tests/test_component_health.py`
- `tests/test_runtime_health.py`

Related:
- `tests/test_cache_resiliency.py`
- `tests/test_matcher_smoke.py`

```bash
python -m pytest tests/test_plex_stale_resolution.py tests/test_component_health.py tests/test_runtime_health.py -v
```

Before finalizing significant changes:

```bash
python -m pytest -v
```

## 18. Design Decisions and ADR References

- ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority
- ADR-007 — Isolate Optional Integration Failures
- ADR-009 — Target Headless Containerized Deployment

## 19. Operational Notes

Troubleshooting should separate connection, authentication, library selection, metadata retrieval, cached matching, live resolution, and playlist modification.

### Cache Bypass Performance (`--no-cache`)

When troubleshooting with `--no-cache`, expect significantly longer processing times because the application bypasses the local Plex library cache and relies directly on Plex. With large libraries, this may increase execution time from normal cache-backed performance to several minutes or longer.

During development with a library of approximately 55,000 tracks, direct Plex operation was observed to take roughly **10 minutes or more** in some runs. This is an operational observation rather than a guaranteed benchmark.

See `docs/subsystems/cache.md` for additional operational guidance.

## 20. Security Considerations

The Plex token must be treated as sensitive. Future deployment should consider configuration permissions, container secret handling, backup protection, and log sanitization.

## 21. Future Considerations

Potential improvements include better health diagnostics, stale-cache reporting, playlist-operation statistics, dashboard visibility, container connection validation, credential management, and temporary-outage resiliency.

> Use Plex when live Plex authority is required, and avoid requiring Plex when safe local work can continue without it.

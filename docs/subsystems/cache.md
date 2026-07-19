# Plex Library Cache Subsystem

## 1. Purpose and Scope

The Plex library cache subsystem maintains a local SQLite representation of relevant Plex music-library metadata. It exists primarily to avoid repeatedly retrieving and processing the entire Plex music library during playlist matching.

The cache is a performance and resiliency layer. It is not authoritative; Plex remains the authoritative source for the live library.

The governing decision is `ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority`.

## 2. Responsibilities

The cache persists relevant Plex track metadata, records refresh metadata, supplies cached tracks for `SearchIndex` construction, evaluates cache freshness, and replaces cached contents after a successful refresh.

It does not create Plex playlists, determine matches, acquire media, or guarantee that a cached track still exists in live Plex.

## 3. Processing Flow

### Cache Loading and Search Index Construction

```text
Application Startup
playlist_import_v2.py
        |
        v
Cache Configuration
[cache] (config.ini)
        |
        v
LibraryCache (cache.py)
        |
        v
cache/plex_library.db
  |-- metadata
  |-- tracks
        |
        v
Track Objects (models.py)
        |
        v
SearchIndex (search_index.py)
        |
        v
Matching (matcher.py)
```

### Cache Refresh Flow

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
                  playlist_import_v2.py
                           |
                           v
                    Connect to Plex
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
                Application Track Records
                      (models.py)
                           |
                           v
                 Replace Cached Tracks
              LibraryCache.replace_tracks()
                       (cache.py)
                           |
                           v
                 cache/plex_library.db
                    |             |
                    v             v
              table: tracks  table: metadata
                           |
                           v
               Build / Rebuild SearchIndex
                    (search_index.py)
                           |
                           v
                  Matching Subsystem
                     (matcher.py)
```

A cache refresh can be initiated explicitly with the `--refresh-cache` command-line option or automatically when the existing cache exceeds the configured `max_age_hours` freshness threshold. Both paths converge on the same cache-refresh process. If the cache remains within the configured freshness window and no manual refresh is requested, the existing cached library data is used.

A failed live refresh should not intentionally destroy a previously usable cache.

## 4. Persistent Database

Database: `cache/plex_library.db`

Owned by: `cache.py`

Tables:
- `metadata`
- `tracks`

## 5. Cache Configuration

Representative settings:

```ini
[cache]
enabled=true
database=cache/plex_library.db
refresh_on_start=false
max_age_hours=24
```

Detailed setting descriptions belong in `docs/configuration.md`.

## 6. Cache Freshness

Freshness is an age policy, not a guarantee that the cache exactly matches live Plex. A cache can be fresh according to age while still containing a track removed from Plex after the last refresh.

## 7. Cache Refresh

A successful refresh replaces the cached library representation with current data retrieved from Plex and updates refresh metadata.

## 8. Search Index Relationship

SQLite provides persistent storage between runs. `SearchIndex` provides fast in-memory lookup during a run. Matching normally queries `SearchIndex`, not SQLite directly.

## 9. Relationship to Live Plex

Cached metadata supports matching. Live Plex identity is required when performing actual Plex operations.

## 10. Stale Cache Entries

A cached match may be valid according to cached metadata but fail later when its live Plex object no longer exists. Matching failure and live-resolution failure must remain distinct.

## 11. Plex-Unavailable Operation

With a usable cache, parsing, matching, reporting, and appropriate downstream work may continue when Plex is unavailable. Plex playlist modification cannot.

## 12. Empty Cache

A stale cache may still be useful for degraded matching. An empty cache cannot provide meaningful library matching.

## 13. Database Integrity

Corruption, schema incompatibility, or unreadable data should not be silently treated as an ordinary empty library.

## 14. Schema Versioning

Current cache schema: `SCHEMA_VERSION = 1`.

Because `plex_library.db` is reproducible from Plex, rebuilding may be preferable to complex migration when no unique state would be lost.

## 15. Failure Behavior

Cache read, refresh, write, and stale live-resolution failures should be reported distinctly. Failed refreshes should preserve an existing usable cache where practical.

## 16. Logging and Observability

Logging should expose cache enablement, path, track count, last refresh, freshness, refresh attempts/results, degraded operation, and stale live-resolution events.

## 17. Testing

Primary coverage:
- `tests/test_cache_resiliency.py`
- `tests/test_plex_stale_resolution.py`

Related:
- `tests/test_component_health.py`
- `tests/test_runtime_health.py`
- `tests/test_matcher_smoke.py`

Run primary tests:

```bash
python -m pytest tests/test_cache_resiliency.py tests/test_plex_stale_resolution.py -v
```

Run full regression suite before finalizing significant changes:

```bash
python -m pytest -v
```

## 18. Design Decisions and ADR References

- ADR-003 — Use Embedded SQLite for Local Persistence
- ADR-006 — Treat the Plex Library Cache as a Performance Layer, Not the Authority
- ADR-007 — Isolate Optional Integration Failures

## 19. Operational Notes

When investigating cache problems, verify configuration, database existence/readability, track count, refresh metadata, Plex availability during refresh, and whether failure occurs during matching or live Plex resolution.

### Direct Plex Matching (`--no-cache`)

When `--no-cache` is used, the application bypasses the local Plex library cache and relies on direct Plex access for library matching. This can be significantly slower than cache-backed operation, particularly with large music libraries.

During development and testing with a Plex library of approximately 55,000 tracks, direct Plex operation could require **10 minutes or more**, compared with substantially faster cache-backed matching. Actual duration depends on Plex server performance, network conditions, library size, and system resources.

For normal operation with large libraries, cache-backed matching is recommended. The `--no-cache` option is better suited to troubleshooting, validation, or situations where bypassing cached library data is specifically required.

## 20. Backup and Recovery

`cache/plex_library.db` is reproducible from Plex and has lower backup priority than databases containing unique historical state, though preserving it can improve recovery and degraded-operation capability.

## 21. Future Considerations

Potential improvements include cache-health reporting, refresh statistics, stale-identity metrics, dashboard presentation, and migration tooling if needed.

> Use the cache to make Plex library matching fast and resilient, but never confuse cached knowledge with current Plex reality.

# ADR-003 — Use Embedded SQLite for Local Persistence

**Status:** Accepted  
**Decision:** Use embedded SQLite databases for local application persistence rather than requiring an external database service.

## Context

The application persists Plex cache data, alias usage, Lidarr search history, and XMPlaylist history/state.

## Decision

Use embedded SQLite databases:

- `cache/plex_library.db`
- `cache/alias_usage.db`
- `cache/lidarr_search_history.db`
- `cache/xmplaylist_history.db`

Each store belongs to the subsystem responsible for its data.

## Rationale

SQLite provides structured, durable, transactional persistence without a separate database server, credentials, daemon, or network dependency. This fits self-contained and future containerized deployment.

## Alternatives Considered

External database servers, a single shared SQLite database, and flat files.

## Consequences

Positive: simple deployment, structured persistence, subsystem ownership, straightforward file backup.

Negative: schema changes require migration consideration; SQLite locking/concurrency must be respected; persistent volumes are required for container deployment.

## Future Reconsideration

Reconsider if multiple instances require coordinated writes, distributed deployment emerges, high write concurrency develops, or a shared multi-host datastore becomes necessary.
